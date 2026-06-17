"""
イベントソースポリシーチェッカー

自動取得前に合法性を確認する。
- auto_fetch_allowed = True
- 現在日時 < expires_at
条件を満たさない場合は取得を中止しログ出力。
"""

from datetime import datetime
from sqlalchemy.orm import Session
import logging

from models.event_source_policy import EventSourcePolicy

logger = logging.getLogger(__name__)


class SourcePolicyError(Exception):
    """ソースポリシー違反時のエラー"""

    pass


class EventSourceChecker:
    """ソースポリシーの合法性を確認するチェッカー"""

    def __init__(self, db: Session):
        self.db = db

    def check_source_allowed(self, source_name: str) -> bool:
        """
        指定ソースの自動取得が許可されているか確認する。

        Returns:
            True: 取得許可
        Raises:
            SourcePolicyError: 取得不可の場合
        """
        policy = (
            self.db.query(EventSourcePolicy)
            .filter(EventSourcePolicy.source_name == source_name)
            .first()
        )

        if policy is None:
            msg = f"ソースポリシー未登録: {source_name}"
            logger.error(msg)
            raise SourcePolicyError(msg)

        # 自動取得許可フラグチェック
        if not policy.auto_fetch_allowed:
            msg = f"自動取得不許可: {source_name} (auto_fetch_allowed=False)"
            logger.warning(msg)
            raise SourcePolicyError(msg)

        # 有効期限チェック
        now = (
            datetime.now(policy.expires_at.tzinfo)
            if policy.expires_at.tzinfo
            else datetime.now()
        )
        if now >= policy.expires_at:
            msg = (
                f"ソースポリシー期限切れ: {source_name} "
                f"(expires_at={policy.expires_at.isoformat()}, now={now.isoformat()})"
            )
            logger.warning(msg)
            raise SourcePolicyError(msg)

        logger.info(
            f"ソースポリシーOK: {source_name} "
            f"(legal_basis={policy.legal_basis}, expires_at={policy.expires_at.isoformat()})"
        )
        return True

    def get_policy_info(self, source_name: str) -> dict:
        """ポリシー情報を辞書形式で取得（デバッグ用）"""
        policy = (
            self.db.query(EventSourcePolicy)
            .filter(EventSourcePolicy.source_name == source_name)
            .first()
        )

        if policy is None:
            return {"error": "未登録"}

        return {
            "source_name": policy.source_name,
            "source_type": policy.source_type,
            "legal_basis": policy.legal_basis,
            "terms_url": policy.terms_url,
            "auto_fetch_allowed": policy.auto_fetch_allowed,
            "checked_at": policy.checked_at.isoformat() if policy.checked_at else "-",
            "expires_at": policy.expires_at.isoformat() if policy.expires_at else "-",
            "approved_by": policy.approved_by,
        }
