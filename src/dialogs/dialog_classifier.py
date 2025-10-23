"""
Dialog Classification Module

이 모듈은 전자결재 시스템의 다양한 대화상자 텍스트를 분석하고 적절한 액션을 결정하는
중앙화된 처리 로직을 제공합니다.
"""

import logging
from enum import Enum
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class DialogAction(Enum):
    """대화상자 텍스트 분석 결과로 수행할 액션을 정의합니다."""

    CONTINUE = "continue"  # 다음 문서 처리 또는 계속 진행
    EXIT = "exit"  # 프로세스 종료
    APPROVE = "approve"  # 결재 승인 진행
    CANCEL_APPROVE = "cancel_approve"  # 결재 취소 진행
    UNKNOWN = "unknown"  # 알 수 없는 대화상자


class DialogClassifier:
    """
    대화상자 텍스트를 분석하여 적절한 액션을 결정하는 분류기입니다.

    전자결재 시스템에서 나타나는 다양한 확인 대화상자의 텍스트를 분석하고
    해당 상황에 맞는 액션을 결정합니다.
    """

    def __init__(self) -> None:
        """DialogClassifier 인스턴스를 초기화합니다."""
        self._pattern_mapping = self._initialize_patterns()
        self._debug_mode = False

    def _initialize_patterns(self) -> Dict[DialogAction, List[str]]:
        """
        대화상자 텍스트 패턴을 액션별로 매핑하는 딕셔너리를 초기화합니다.

        Returns:
            Dict[DialogAction, List[str]]: 액션별 텍스트 패턴 매핑
        """
        return {
            # 종료 관련 패턴들 (우선순위가 높은 정확한 패턴부터)
            DialogAction.EXIT: [
                "종료하시겠습니까",
                "결재문서가 완료되었습니다.\n\n종료하시겠습니까?",
                "종료",
                "끝",
                "완료",
            ],
            # 다음 문서 처리 관련 패턴들
            DialogAction.CONTINUE: [
                "결재문서가 완료되었습니다",  # 핵심 패턴 - 가장 먼저 매칭
                "다음 문서를 처리하겠습니까",  # 두 번째 핵심 패턴
                "다음 문서를 처리하겠습니다",
                "문서를 처리하겠습니까",
                "다음 문서",
                "다음",
                "완료되었습니다",  # 더 짧은 백업 패턴
            ],
            # 결재 승인 진행 관련 패턴들
            DialogAction.APPROVE: ["결재를 진행하시겠습니까", "결재 진행"],
            # 결재 취소 진행 관련 패턴들 (더 구체적인 패턴을 먼저)
            DialogAction.CANCEL_APPROVE: ["취소 결재를 진행하시겠습니까", "취소 결재"],
        }

    def set_debug_mode(self, enabled: bool) -> None:
        """디버그 모드를 설정합니다."""
        self._debug_mode = enabled
        if enabled:
            logger.info("DialogClassifier 디버그 모드가 활성화되었습니다.")

    def classify_dialog_action(self, dialog_text: str) -> DialogAction:
        """
        대화상자 텍스트를 분석하여 적절한 액션을 결정합니다.

        Args:
            dialog_text (str): 분석할 대화상자 텍스트

        Returns:
            DialogAction: 결정된 액션
        """
        if not dialog_text or not dialog_text.strip():
            logger.warning("빈 대화상자 텍스트가 전달되었습니다.")
            return DialogAction.UNKNOWN

        normalized_text = dialog_text.strip()

        # 디버그 정보 강제 출력 (임시)
        if self._debug_mode:
            logger.info("��ȭ���� �ؽ�Ʈ �м� ����: '%s'", normalized_text)
            logger.info(
                "�ؽ�Ʈ ����: %d, �ٹٲ� ����: %s",
                len(normalized_text),
                '\n' in normalized_text,
            )

        # 패턴 길이 순으로 정렬하여 더 구체적인 패턴이 먼저 매칭되도록 함
        all_patterns = []
        for action, patterns in self._pattern_mapping.items():
            for pattern in patterns:
                all_patterns.append((pattern, action, len(pattern)))

        # 패턴을 길이 순으로 내림차순 정렬 (긴 패턴이 먼저)
        all_patterns.sort(key=lambda x: x[2], reverse=True)

        # 정렬된 순서대로 패턴 매칭 시도
        for pattern, action, _ in all_patterns:
            logger.debug(
                f"패턴 테스트: '{pattern}' in '{normalized_text[:50]}...' = {pattern in normalized_text}"
            )
            if pattern in normalized_text:
                logger.info(f"패턴 매칭 성공: '{pattern}' → {action.value}")
                return action

        # 패턴이 매칭되지 않은 경우
        logger.warning(f"알 수 없는 대화상자 패턴: '{normalized_text}'")
        return DialogAction.UNKNOWN

    def get_action_description(self, action: DialogAction) -> str:
        """
        액션에 대한 한국어 설명을 반환합니다.

        Args:
            action (DialogAction): 설명을 얻을 액션

        Returns:
            str: 액션에 대한 한국어 설명
        """
        descriptions = {
            DialogAction.CONTINUE: "다음 문서 처리 또는 계속 진행",
            DialogAction.EXIT: "프로세스 종료",
            DialogAction.APPROVE: "결재 승인 진행",
            DialogAction.CANCEL_APPROVE: "결재 취소 진행",
            DialogAction.UNKNOWN: "알 수 없는 액션",
        }
        return descriptions.get(action, "정의되지 않은 액션")

    def add_pattern(self, action: DialogAction, pattern: str) -> None:
        """
        새로운 패턴을 추가합니다.

        Args:
            action (DialogAction): 패턴을 추가할 액션
            pattern (str): 추가할 패턴
        """
        if action not in self._pattern_mapping:
            self._pattern_mapping[action] = []

        if pattern not in self._pattern_mapping[action]:
            self._pattern_mapping[action].append(pattern)
            logger.info(f"새 패턴 추가: {action.value} ← '{pattern}'")
        else:
            logger.warning(f"이미 존재하는 패턴: {action.value} ← '{pattern}'")

    def get_patterns_for_action(self, action: DialogAction) -> List[str]:
        """
        특정 액션에 대한 모든 패턴을 반환합니다.

        Args:
            action (DialogAction): 패턴을 조회할 액션

        Returns:
            List[str]: 해당 액션의 모든 패턴들
        """
        return self._pattern_mapping.get(action, []).copy()

    def analyze_dialog_comprehensive(self, dialog_text: str) -> Dict[str, Any]:
        """
        대화상자 텍스트에 대한 종합적인 분석 결과를 반환합니다.

        Args:
            dialog_text (str): 분석할 대화상자 텍스트

        Returns:
            Dict[str, any]: 분석 결과 딕셔너리
        """
        action = self.classify_dialog_action(dialog_text)

        # 각 액션에 대한 매칭 점수 계산
        matching_scores = {}
        for check_action, patterns in self._pattern_mapping.items():
            score = 0
            matched_patterns = []
            for pattern in patterns:
                if pattern in dialog_text:
                    score += len(pattern)  # 더 긴 패턴에 더 높은 점수
                    matched_patterns.append(pattern)
            matching_scores[check_action.value] = {
                "score": score,
                "matched_patterns": matched_patterns,
            }

        return {
            "original_text": dialog_text,
            "normalized_text": dialog_text.strip(),
            "determined_action": action.value,
            "action_description": self.get_action_description(action),
            "matching_scores": matching_scores,
            "confidence": "high" if action != DialogAction.UNKNOWN else "low",
        }
