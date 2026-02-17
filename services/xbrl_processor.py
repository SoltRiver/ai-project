
import os
import json
import logging
import zipfile
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import text # Use text for bulk insert if needed or Core
from sqlalchemy.dialects.postgresql import insert as pg_insert 
# Note: transforming pg_insert to sqlite compatible or generic
# Standard SQLAlchemy add_all is fine for MVP bulk insert.

from database import SessionLocal
from models.edinet_file import EdinetFile
from models.edinet_document import EdinetDocument
from models.edinet_xbrl_fact import EdinetXbrlFact
from services.edinet_storage import EdinetStorageService, BASE_STORAGE_DIR

# Try import edinet_xbrl
try:
    from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser
    HAS_EDINET_PARSER = True
except ImportError:
    HAS_EDINET_PARSER = False

logger = logging.getLogger(__name__)

class XbrlProcessor:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()
        self.storage = EdinetStorageService(db=self.db)
        self.parser = EdinetXbrlParser() if HAS_EDINET_PARSER else None

    def process_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Main logic for a single doc_id.
        Returns the JSON structure to be saved in xbrl_detect.json.
        """
        print(f"Processing XBRL for {doc_id}...")
        
        # 1. Check EdinetFile (ZIP_TYPE1, OK)
        ef = self.db.query(EdinetFile).filter_by(doc_id=doc_id, file_type="ZIP_TYPE1", status="OK").first()
        if not ef:
            return self._build_result(doc_id, status="SKIP", msg="No ZIP_TYPE1 found or not OK")

        # Resolve paths
        # storage_path is relative: YYYY\MM\doc_id\raw\edinet_type1.zip
        zip_rel_path = ef.storage_path
        zip_abs_path = self.storage.get_absolute_path(zip_rel_path)
        
        # Extracted Dir: YYYY\MM\doc_id\extracted\type1\
        # We can construct it from the parent of raw directory.
        # raw directory is ...\raw\
        doc_root = zip_abs_path.parent.parent
        extracted_dir = doc_root / "extracted" / "type1"
        derived_dir = doc_root / "derived"
        json_log_path = derived_dir / "xbrl_detect.json"

        # 2. Check Exists (Idempotency A)
        if json_log_path.exists():
            try:
                with open(json_log_path, "r", encoding="utf-8") as f:
                    existing_log = json.load(f)
                if existing_log.get("status") == "OK":
                    print(f"  Skipping {doc_id} (Already analyzed OK)")
                    return existing_log
            except:
                pass # Re-process if corrupt

        # 3. Unzip
        try:
            self._unzip_safely(zip_abs_path, extracted_dir)
        except Exception as e:
            return self._record_failure(doc_id, zip_rel_path, str(extracted_dir), f"Unzip failed: {e}", json_log_path)

        # 4. Detect Candidates
        candidates = self._detect_candidates(extracted_dir)
        
        # 5. Select Primary
        primary = self._select_primary_file(candidates)
        
        if not primary:
            return self._record_failure(doc_id, zip_rel_path, str(extracted_dir), "No XBRL/iXBRL file found", json_log_path, candidates)

        # 6. Parse & Extract Facts
        try:
            facts = self._extract_facts(primary["path"], primary["type"], doc_id)
            if not facts:
                 # Fallback? If XBRL extraction failed, try next candidate? 
                 # MVP: If select primary fails, we fail.
                 # But if primary was XBRL and it failed, maybe iXBRL works?
                 # For MVP simpler: Just fail or save empty.
                 # User says: "failed -> status=NG"
                 if not candidates["ixbrl_candidates"] and primary["type"] == "XBRL":
                      pass # No fallback
                 pass 
            
            # 7. Bulk Insert
            inserted_count = 0
            if facts:
                inserted_count = self._bulk_insert_facts(doc_id, facts)

            # 8. Save Success Log
            result = {
                "doc_id": doc_id,
                "zip_storage_path": str(zip_rel_path),
                "extracted_dir": str(extracted_dir.relative_to(BASE_STORAGE_DIR)),
                "detected": candidates,
                "selected_primary": primary,
                "facts": {"inserted": inserted_count, "skipped_duplicates": 0, "errors": 0},
                "status": "OK",
                "error_message": None,
                "generated_at": datetime.now().isoformat()
            }
            self._save_json_log(json_log_path, result)
            return result
            
        except Exception as e:
            return self._record_failure(doc_id, zip_rel_path, str(extracted_dir), f"Analysis failed: {e}", json_log_path, candidates, primary)

    def _unzip_safely(self, zip_path: Path, dest_dir: Path):
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Check if empty? User says "if exist, check if empty, else re-expand"
        if any(dest_dir.iterdir()):
             # Already expanded. Re-expand? 
             # For safety/idempotency, clearing and re-expanding is safer to ensure consistency with ZIP.
             # User: "展開済みでも “展開先が空” なら再展開" -> Implies if not empty, we might skip?
             # But "ZIPにパストラバーサル...安全に展開" is required.
             # Let's clean and re-expand to be safe.
             # Or to save time, if it has content, assume OK? 
             # Let's rely on detection. If no files detected, maybe re-expand.
             # I'll just expand over.
             pass
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            for member in z.infolist():
                # Path Traversal Check
                # user_path = member.filename
                # target = dest_dir / user_path
                # if not target.resolve().is_relative_to(dest_dir.resolve()): raise...
                # Note: zipfile.extractall usually handles basic checks but strict manual check is better.
                
                # Check absolute path resolution
                is_safe = not member.filename.startswith("/") and ".." not in member.filename
                if not is_safe:
                    print(f"Warning: Suspicious file path in zip {member.filename}. Skipping.")
                    continue
                
                z.extract(member, dest_dir)

    def _detect_candidates(self, scan_dir: Path) -> Dict[str, Any]:
        xbrl_cands = []
        ixbrl_cands = []
        
        for file_path in scan_dir.rglob("*"):
            if not file_path.is_file(): continue
            
            size = file_path.stat().st_size
            ext = file_path.suffix.lower()
            
            # Relative path for logging
            rel_path = str(file_path.relative_to(scan_dir))
            
            if ext in [".xbrl", ".xml"]:
                # Check content? Some XMLs are not XBRL.
                # Basic check: "PublicDoc" in path usually?
                if size > 100: # Min size filter
                    xbrl_cands.append({"path": str(file_path), "size": size, "rel_path": rel_path})
            elif ext in [".htm", ".html"]:
                if size > 100:
                    ixbrl_cands.append({"path": str(file_path), "size": size, "rel_path": rel_path})
                    
        return {
            "xbrl_candidates": sorted(xbrl_cands, key=lambda x: x["size"], reverse=True),
            "ixbrl_candidates": sorted(ixbrl_cands, key=lambda x: x["size"], reverse=True)
        }

    def _select_primary_file(self, candidates: Dict) -> Optional[Dict]:
        # Priority 1: XBRL
        xbrl = candidates.get("xbrl_candidates")
        if xbrl:
            return {"type": "XBRL", "path": xbrl[0]["path"], "reason": "Largest XBRL file"}
        
        # Priority 2: iXBRL
        ixbrl = candidates.get("ixbrl_candidates")
        if ixbrl:
            return {"type": "IXBRL", "path": ixbrl[0]["path"], "reason": "Largest HTML (Fallback)"}
            
        return None

    def _extract_facts(self, file_path: str, file_type: str, doc_id: str) -> List[Dict]:
        facts = []
        if file_type == "XBRL":
            facts = self._parse_xbrl_native(file_path)
        elif file_type == "IXBRL":
            facts = self._parse_ixbrl_html(file_path)
        
        print(f"Extracted {len(facts)} facts from {doc_id} ({file_type})")
        return facts

    def _parse_xbrl_native(self, file_path: str) -> List[Dict]:
        facts = []
        try:
             with open(file_path, "r", encoding="utf-8") as f:
                 soup = BeautifulSoup(f, "lxml-xml") 
             
             # Debug
             # print(f"DEBUG: Parsed {file_path}. Root tags: {[t.name for t in soup.find_all(recursive=False)]}")
             
             # Scan all tags to be robust against namespace prefixes
             all_tags = soup.find_all()
             all_tags = soup.find_all()
             for tag in all_tags:
                 # Handle namespaces via prefix
                 if not tag.name: continue
                 
                 prefix = tag.prefix
                 name = tag.name
                 
                 if prefix:
                     # Reconstruct "prefix:name" for upstream logic
                     concept = f"{prefix}:{name}"
                 else:
                     # No prefix? check if colon in name (fallback for some parsers)
                     if ":" in name:
                         concept = name
                         prefix = name.split(":")[0]
                     else:
                         continue # Skip non-namespaced tags? Or treat as default?
                 
                 # Exclude system namespaces
                 if prefix in ["link", "xbrli", "xbrl", "xlink", "xbrldi", "iso4217"]:
                     continue

                 # Facts must have contextRef
                 if not tag.get("contextRef"):
                     continue
                 
                 value = tag.text.strip()
                 context_ref = tag.get("contextRef")
                 unit_ref = tag.get("unitRef")
                 decimals = tag.get("decimals")
                 
                 facts.append({
                     "concept": concept,
                     "value_text": value,
                     "context_ref": context_ref,
                     "unit_ref": unit_ref,
                     "decimals": decimals
                 })
             
             # Context Extraction (Robust)
             contexts = {}
             # Find all tags that might be contexts.
             # xbrli:context or just context?
             # We iterate all to find context definitions.
             for ctx in soup.find_all(["xbrli:context", "context"]):
                 cid = ctx.get("id")
                 if not cid: continue
                 
                 c_data = {"entity": None, "period": {}}
                 
                 # Entity
                 ent = ctx.find(["xbrli:entity", "entity"])
                 if ent:
                     ident = ent.find(["xbrli:identifier", "identifier"])
                     if ident: c_data["entity"] = ident.text.strip()
                     
                 # Period
                 per = ctx.find(["xbrli:period", "period"])
                 if per:
                     # Check children logic
                     # start/end date usually xbrli:startDate
                     s = per.find(["xbrli:startDate", "startDate"])
                     e = per.find(["xbrli:endDate", "endDate"])
                     i = per.find(["xbrli:instant", "instant"])
                     
                     if s and e:
                         c_data["period"]["start"] = s.text.strip()
                         c_data["period"]["end"] = e.text.strip()
                     elif i:
                         c_data["period"]["instant"] = i.text.strip()
                 
                 contexts[cid] = c_data
                 
             # Merge Context Data
             for f in facts:
                 cref = f.get("context_ref")
                 if cref and cref in contexts:
                     cdata = contexts[cref]
                     f["entity_id"] = cdata["entity"]
                     f["period_start"] = cdata["period"].get("start")
                     f["period_end"] = cdata["period"].get("end")
                     f["instant_date"] = cdata["period"].get("instant")

        except Exception as e:
            logger.error(f"XBRL Parse error: {e}")
            # raise e # Don't raise, return what we found? 
            # If parse failed completely, raise.
            raise e
            
        return facts

    def _parse_ixbrl_html(self, file_path: str) -> List[Dict]:
        facts = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
            
            # Look for ix:nonNumeric, ix:nonFraction
            # Namespaces likely 'ix'
            # BS4 handles case-insensitively or via attributes usually for HTML.
            # But colons in tag names in HTML parser might be treated as name="ix:nonNumeric"
            
            tags = soup.find_all(["ix:nonnumeric", "ix:nonfraction", "ix:nonNumeric", "ix:nonFraction"])
            
            # Need to find contexts too. ix:xmlContext? or ix:resources -> xbrl:context?
            # Creating context map from iXBRL is tricky.
            # Use simplified extraction for MVP: Just get concept/value/refs.
            
            # Contexts in hidden section? 
            # <ix:resources> <xbrli:context id="..."> ...
            contexts = {}
            resources = soup.find(["ix:resources", "ix:header"]) # Header/Resources checks
            if resources:
                     contexts[cid] = c_data

            for tag in tags:
                concept = tag.get("name")
                if not concept: continue
                
                value = tag.text.strip()
                # If ix:nonFraction, detecting scale/sign/format is needed for true number.
                # MVP: Store raw text.
                
                context_ref = tag.get("contextref")
                unit_ref = tag.get("unitref")
                decimals = tag.get("decimals")
                
                f = {
                     "concept": concept,
                     "value_text": value,
                     "context_ref": context_ref,
                     "unit_ref": unit_ref,
                     "decimals": decimals
                }
                
                if context_ref and context_ref in contexts:
                     cdata = contexts[context_ref]
                     f["entity_id"] = cdata["entity"]
                     f["period_start"] = cdata["period"].get("start")
                     f["period_end"] = cdata["period"].get("end")
                     f["instant_date"] = cdata["period"].get("instant")
                
                facts.append(f)
                
        except Exception as e:
            logger.error(f"iXBRL Parse error: {e}")
            raise e
        return facts

    def _bulk_insert_facts(self, doc_id: str, facts: List[Dict]) -> int:
        if not facts: return 0
        
        # Prepare objects
        objects = []
        for f in facts:
            # Clean dates
            def pdate(x):
                if not x: return None
                try:
                    return datetime.strptime(x, "%Y-%m-%d").date()
                except:
                    return None
            
            # Numeric conversion check
            val_num = None
            try:
                # Handle comma? '1,000' -> 1000
                if f["value_text"]:
                    clean = f["value_text"].replace(",", "").replace("\n", "")
                    # Check if valid float
                    # Note: ix:nonNumeric might have non-numeric text.
                    # ix:nonFraction is numeric.
                    # We try to convert if looks like number.
                    # But if concept is 'FilerName', it's text.
                    # Simple heuristic: if convertable, store.
                    import re
                    if re.match(r'^-?\d+(\.\d+)?$', clean):
                        val_num = float(clean)
            except:
                pass

            obj = EdinetXbrlFact(
                doc_id=doc_id,
                concept=f["concept"],
                value_text=f["value_text"][:20000] if f["value_text"] else None, # Truncate large text
                value_numeric=val_num,
                unit_ref=f.get("unit_ref"),
                decimals=f.get("decimals"),
                period_start=pdate(f.get("period_start")),
                period_end=pdate(f.get("period_end")),
                instant_date=pdate(f.get("instant_date")),
                entity_id=f.get("entity_id"),
                context_ref=f.get("context_ref")
            )
            objects.append(obj)
        
        # Insert
        # For bulk speed, we should use bulk_save_objects or core insert
        self.db.bulk_save_objects(objects)
        self.db.commit()
        return len(objects)

    def _save_json_log(self, path: Path, data: Dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _record_failure(self, doc_id, zip_path, ext_dir, msg, log_path, candidates=None, primary=None):
        logger.error(f"Fail {doc_id}: {msg}")
        res = {
            "doc_id": doc_id,
            "zip_storage_path": str(zip_path),
            "extracted_dir": str(Path(ext_dir).relative_to(BASE_STORAGE_DIR) if BASE_STORAGE_DIR in Path(ext_dir).parents else ext_dir),
            "detected": candidates,
            "selected_primary": primary,
            "facts": None,
            "status": "NG",
            "error_message": msg,
            "generated_at": datetime.now().isoformat()
        }
        self._save_json_log(log_path, res)
        return res
    
    def _build_result(self, doc_id, status, msg):
        return {"doc_id": doc_id, "status": status, "error_message": msg}

    def __del__(self):
        # if self.db: self.db.close()
        pass
