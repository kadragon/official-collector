"""
DialogClassifier 클래스에 대한 단위 테스트
"""

import pytest
from src.dialogs.dialog_classifier import DialogClassifier, DialogAction


class TestDialogClassifier:
    """DialogClassifier 클래스의 테스트 클래스"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 초기화"""
        self.processor = DialogClassifier()

    def test_classify_exit_actions(self):
        """종료 관련 액션 분류 테스트"""
        exit_texts = [
            "종료하시겠습니까",
            "결재문서가 완료되었습니다.\n\n종료하시겠습니까?",
            "종료",
            "끝",
            "완료",
        ]

        for text in exit_texts:
            result = self.processor.classify_dialog_action(text)
            assert result == DialogAction.EXIT, f"'{text}' should be classified as EXIT"

    def test_classify_continue_actions(self):
        """계속 진행 관련 액션 분류 테스트"""
        continue_texts = [
            "다음 문서를 처리하겠습니다",
            "문서를 처리하겠습니까",
            "결재문서가 완료되었습니다.\n\n다음 문서를 처리하겠습니까?",
            "다음 문서",
            "다음",
        ]

        for text in continue_texts:
            result = self.processor.classify_dialog_action(text)
            assert (
                result == DialogAction.CONTINUE
            ), f"'{text}' should be classified as CONTINUE"

    def test_classify_approve_actions(self):
        """결재 승인 관련 액션 분류 테스트"""
        approve_texts = ["결재를 진행하시겠습니까", "결재 진행"]

        for text in approve_texts:
            result = self.processor.classify_dialog_action(text)
            assert (
                result == DialogAction.APPROVE
            ), f"'{text}' should be classified as APPROVE"

    def test_classify_cancel_approve_actions(self):
        """결재 취소 관련 액션 분류 테스트"""
        cancel_approve_texts = ["취소 결재를 진행하시겠습니까", "취소 결재"]

        for text in cancel_approve_texts:
            result = self.processor.classify_dialog_action(text)
            assert (
                result == DialogAction.CANCEL_APPROVE
            ), f"'{text}' should be classified as CANCEL_APPROVE"

    def test_classify_unknown_actions(self):
        """알 수 없는 텍스트 분류 테스트"""
        unknown_texts = ["알 수 없는 대화상자", "임의의 텍스트", "확인", "", "   "]

        for text in unknown_texts:
            result = self.processor.classify_dialog_action(text)
            assert (
                result == DialogAction.UNKNOWN
            ), f"'{text}' should be classified as UNKNOWN"

    def test_empty_and_whitespace_text(self):
        """빈 문자열과 공백 문자열 처리 테스트"""
        empty_texts = ["", "   ", "\n\t  ", None]

        for text in empty_texts:
            if text is None:
                continue  # None은 실제로는 전달되지 않음
            result = self.processor.classify_dialog_action(text)
            assert (
                result == DialogAction.UNKNOWN
            ), f"'{text}' should be classified as UNKNOWN"

    def test_pattern_priority(self):
        """패턴 우선순위 테스트 - 더 구체적인 패턴이 우선되어야 함"""
        # 더 구체적인 패턴이 먼저 매칭되어야 함
        text_with_multiple_patterns = (
            "결재문서가 완료되었습니다.\n\n종료하시겠습니까? 다음"
        )
        result = self.processor.classify_dialog_action(text_with_multiple_patterns)
        # 더 긴 구체적 패턴인 "결재문서가 완료되었습니다.\n\n종료하시겠습니까?"이 매칭되어야 함
        assert result == DialogAction.EXIT

    def test_case_sensitivity(self):
        """대소문자 구분 테스트"""
        # 한글이므로 대소문자 이슈는 없지만, 정확한 매칭 확인
        exact_text = "종료하시겠습니까"
        result = self.processor.classify_dialog_action(exact_text)
        assert result == DialogAction.EXIT

    def test_partial_matching(self):
        """부분 매칭 테스트"""
        # 긴 문자열 내에 패턴이 포함된 경우
        long_text = "현재 작업이 완료되었습니다. 종료하시겠습니까? 다른 작업을 계속하시겠습니까?"
        result = self.processor.classify_dialog_action(long_text)
        assert result == DialogAction.EXIT  # 종료 패턴이 먼저 나타남

    def test_get_action_description(self):
        """액션 설명 반환 테스트"""
        descriptions = {
            DialogAction.CONTINUE: "다음 문서 처리 또는 계속 진행",
            DialogAction.EXIT: "프로세스 종료",
            DialogAction.APPROVE: "결재 승인 진행",
            DialogAction.CANCEL_APPROVE: "결재 취소 진행",
            DialogAction.UNKNOWN: "알 수 없는 액션",
        }

        for action, expected_desc in descriptions.items():
            result = self.processor.get_action_description(action)
            assert result == expected_desc

    def test_add_pattern(self):
        """새 패턴 추가 테스트"""
        new_pattern = "새로운 테스트 패턴"
        self.processor.add_pattern(DialogAction.CONTINUE, new_pattern)

        # 새 패턴으로 분류가 되는지 확인
        result = self.processor.classify_dialog_action(new_pattern)
        assert result == DialogAction.CONTINUE

        # 패턴 목록에 추가되었는지 확인
        patterns = self.processor.get_patterns_for_action(DialogAction.CONTINUE)
        assert new_pattern in patterns

    def test_get_patterns_for_action(self):
        """특정 액션의 패턴 목록 조회 테스트"""
        exit_patterns = self.processor.get_patterns_for_action(DialogAction.EXIT)

        # 기본 종료 패턴들이 포함되어 있는지 확인
        expected_patterns = ["종료하시겠습니까", "종료", "끝", "완료"]
        for pattern in expected_patterns:
            assert pattern in exit_patterns

    def test_analyze_dialog_comprehensive(self):
        """종합 분석 기능 테스트"""
        test_text = "종료하시겠습니까"
        analysis = self.processor.analyze_dialog_comprehensive(test_text)

        # 분석 결과 구조 확인
        assert "original_text" in analysis
        assert "normalized_text" in analysis
        assert "determined_action" in analysis
        assert "action_description" in analysis
        assert "matching_scores" in analysis
        assert "confidence" in analysis

        # 분석 결과 내용 확인
        assert analysis["original_text"] == test_text
        assert analysis["determined_action"] == DialogAction.EXIT.value
        assert analysis["confidence"] == "high"

    def test_debug_mode(self):
        """디버그 모드 테스트"""
        # 디버그 모드 활성화
        self.processor.set_debug_mode(True)

        # 분류 실행 (로그 출력 확인은 수동으로)
        result = self.processor.classify_dialog_action("종료하시겠습니까")
        assert result == DialogAction.EXIT

        # 디버그 모드 비활성화
        self.processor.set_debug_mode(False)
