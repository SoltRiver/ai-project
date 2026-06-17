import os
from pathlib import Path
from typing import List, Optional, Dict, Any


class EdinetXbrlLocator:
    async def locate_xbrl_files(self, directory: Path) -> Dict[str, Any]:
        """
        Scan directory for .xbrl and .htm (Inline XBRL) files.
        Identify the 'primary' XBRL file (PublicDoc).
        """
        xbrl_files = []
        inline_xbrl_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                full_path = Path(root) / file
                if file.endswith(".xbrl"):
                    xbrl_files.append(str(full_path))
                elif file.endswith(".htm") and ("honbun" in file or "ixbrl" in file):
                    inline_xbrl_files.append(str(full_path))

        primary_xbrl = None

        # Strategy 1: Look for 'PublicDoc' in .xbrl files (Traditional or Instance)
        public_docs = [
            f
            for f in xbrl_files
            if "PublicDoc" in f or "PublicDoc" in os.path.dirname(f)
        ]
        if public_docs:
            # Sort by file size descending (heuristic: main report is largest)
            public_docs.sort(key=lambda x: os.path.getsize(x), reverse=True)
            primary_xbrl = public_docs[0]

        # Strategy 2: If no .xbrl PublicDoc, look for Inline XBRL (.htm)
        if not primary_xbrl and inline_xbrl_files:
            # Look for PublicDoc in path
            public_inlines = [
                f
                for f in inline_xbrl_files
                if "PublicDoc" in f or "PublicDoc" in os.path.dirname(f)
            ]
            if public_inlines:
                public_inlines.sort(key=lambda x: os.path.getsize(x), reverse=True)
                primary_xbrl = public_inlines[0]
            else:
                primary_xbrl = inline_xbrl_files[0]

        # Strategy 3: Fallback to largest .xbrl
        if not primary_xbrl and xbrl_files:
            xbrl_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
            primary_xbrl = xbrl_files[0]

        return {
            "xbrl_files": xbrl_files,
            "inline_xbrl_files": inline_xbrl_files,
            "primary_xbrl": primary_xbrl,
        }
