"""
Dialog handler module for official document automation.
Handles dialog analysis, text extraction, and flow state management.
"""

import time
import io
import sys
from typing import Any
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

from config import TimeoutConfig
from utils.error_handler import setup_logger
from utils.performance_logger import log_execution_time
from dialogs.dialog_classifier import DialogClassifier, DialogAction

logger = setup_logger(__name__)


class DocumentFlowState:
    """문서 처리 흐름 상태를 나타내는 열거형"""

    CONTINUE = "continue"  # 다음 문서 처리 계속
    EXIT = "exit"  # 처리 종료
    UNKNOWN = "unknown"  # 알 수 없는 상태


class DialogHandler:
    """Manages dialog detection, analysis, and flow state for the automation system."""

    def __init__(self, dlg: Any, dialog_classifier: DialogClassifier) -> None:
        """
        Initialize the DialogHandler.

        Args:
            dlg: Main dialog window reference
            dialog_classifier: DialogClassifier instance for dialog action classification
        """
        self.dlg = dlg
        self.dialog_classifier = dialog_classifier

    def find_confirm_dialog(self) -> Any:
        """
        초고속 확인 대화상자 찾기 - 성능 최적화된 버전.

        Returns:
            Any: 확인 대화상자 객체, 없으면 None
        """
        logger.debug("확인 대화상자 초고속 검색 시작")

        # 방법 1: 즉시 존재 여부 확인 (대기 없음)
        try:
            dialog = self.dlg.child_window(title="확인", control_type="Window")
            if dialog.exists():
                logger.debug("즉시 확인 대화상자 발견")
                return dialog
        except Exception as e:
            logger.debug("즉시 확인 실패: %s", e)

        # 방법 2: 짧은 대기시간으로 재시도
        try:
            if self._wait_for_dialog_condition(
                lambda: self.dlg.child_window(
                    title="확인", control_type="Window"
                ).exists(),
                timeout=TimeoutConfig.FAST_DIALOG_IMMEDIATE,
                interval=TimeoutConfig.FAST_DIALOG_INTERVAL,
            ):
                dialog = self.dlg.child_window(title="확인", control_type="Window")
                logger.debug("짧은 대기 후 확인 대화상자 발견")
                return dialog
        except Exception as e:
            logger.debug("짧은 대기 방법 실패: %s", e)

        # 방법 3: Desktop에서 매우 짧게 찾기 (백업)
        try:
            desktop = Desktop(backend="uia")
            desktop_dialog = desktop.window(title="확인", class_name="#32770")
            if desktop_dialog.exists():
                logger.debug("Desktop에서 즉시 확인 대화상자 발견")
                return desktop_dialog
        except Exception as e:
            logger.debug("Desktop 즉시 확인 실패: %s", e)

        logger.debug("초고속 방법으로 확인 대화상자를 찾지 못함")
        return None

    def _wait_for_dialog_condition(
        self, condition: callable, timeout: float, interval: float
    ) -> bool:
        """
        대화상자 조건을 확인합니다 (간소화 버전).

        Args:
            condition: 확인할 조건 함수
            timeout: 최대 대기 시간
            interval: 확인 간격

        Returns:
            bool: 조건 만족 여부
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True
            except Exception as e:
                logger.debug("조건 확인 중 오류: %s", e)
            time.sleep(interval)
        return False

    def analyze_dialog_content(self, confirm_dialog: Any) -> str:
        """
        대화상자의 모든 텍스트 내용을 분석합니다.

        Args:
            confirm_dialog: 분석할 대화상자 객체

        Returns:
            str: 대화상자의 전체 텍스트 내용
        """
        try:
            # 모든 Static 컨트롤에서 텍스트 수집
            static_texts = []
            try:
                static_controls = confirm_dialog.children(class_name="Static")
                for control in static_controls:
                    try:
                        text = control.window_text().strip()
                        if text:  # 빈 텍스트 제외
                            static_texts.append(text)
                    except Exception as exc:
                        logger.debug("Static control text read failed: %s", exc)
                        continue
            except Exception as e:
                logger.debug("Static 컨트롤 수집 실패: %s", e)

            # 전체 대화상자 텍스트도 시도
            try:
                full_text = confirm_dialog.window_text()
                if full_text:
                    static_texts.append(full_text)
            except Exception as exc:
                logger.debug("Confirm dialog full text read failed: %s", exc)

            # 수집된 모든 텍스트 로그 출력
            combined_text = " | ".join(static_texts)
            logger.debug("대화상자 텍스트 내용: %s", static_texts)
            return combined_text

        except Exception as e:
            logger.warning("대화상자 내용 분석 실패: %s", e)
            return ""

    def get_quick_dialog_text(self, confirm_dialog: Any) -> str:
        """
        대화상자 텍스트를 빠르게 가져오는 최적화된 함수.

        Args:
            confirm_dialog: 대화상자 객체

        Returns:
            str: 대화상자 텍스트
        """
        try:
            # 가장 빠른 방법: window_text() 직접 사용
            text = confirm_dialog.window_text()
            if text and text.strip():
                return str(text.strip())

            # 백업: Static 컨트롤에서 빠르게 텍스트 수집
            try:
                static_controls = confirm_dialog.children(class_name="Static")
                for control in static_controls[:3]:  # 최대 3개만 확인
                    try:
                        control_text = control.window_text().strip()
                        if control_text and len(control_text) > 5:  # 의미있는 텍스트만
                            return str(control_text)
                    except Exception as exc:
                        logger.debug("Static control quick text read failed: %s", exc)
                        continue
            except Exception as exc:
                logger.debug("Static control enumeration failed: %s", exc)

            return ""
        except Exception as e:
            logger.debug("빠른 텍스트 가져오기 실패: %s", e)
            return ""

    def get_confirm_dialog_text(self) -> str:
        """
        확인 대화상자의 텍스트 내용을 가져옵니다.

        Returns:
            str: 대화상자의 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if confirm_window.exists():
                # 대화상자 내의 모든 텍스트를 수집
                texts = confirm_window.texts()
                all_text = " ".join(texts) if texts else ""
                # Static 컨트롤에서도 텍스트 수집 시도
                try:
                    static_controls = confirm_window.children(control_type="Text")
                    for control in static_controls:
                        if control.exists():
                            control_text = control.window_text()
                            if control_text and control_text not in all_text:
                                all_text += " " + control_text
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("Static 컨트롤에서 텍스트 수집 실패: %s", e)
                except Exception as e:
                    logger.warning(
                        "Static 컨트롤 텍스트 수집 중 예상치 못한 오류: %s", e
                    )
                # Edit 컨트롤에서도 텍스트 수집 시도
                try:
                    edit_controls = confirm_window.children(control_type="Edit")
                    for control in edit_controls:
                        if control.exists():
                            control_text = control.window_text()
                            if control_text and control_text not in all_text:
                                all_text += " " + control_text
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("Edit 컨트롤에서 텍스트 수집 실패: %s", e)
                except Exception as e:
                    logger.warning("Edit 컨트롤 텍스트 수집 중 예상치 못한 오류: %s", e)
                logger.debug("대화상자에서 수집된 전체 텍스트: '%s'", all_text)
                return all_text
            return ""
        except Exception as e:
            logger.debug("확인 대화상자 텍스트 가져오기 실패: %s", e)
            return ""

    def get_detailed_dialog_text(self) -> str:
        """
        확인 대화상자의 상세 텍스트를 다양한 방법으로 수집합니다.

        Returns:
            str: 대화상자의 상세 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if not confirm_window.exists():
                return ""
            all_texts = []
            # 모든 자식 컨트롤 순회
            try:
                children = confirm_window.children()
                for child in children:
                    try:
                        text = child.window_text()
                        if (
                            text
                            and text.strip()
                            and text != "확인"
                            and text not in all_texts
                        ):
                            all_texts.append(text.strip())
                    except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                        logger.debug("자식 컨트롤 텍스트 읽기 실패: %s", e)
                        continue
                    except Exception as e:
                        logger.warning("자식 컨트롤 처리 중 예상치 못한 오류: %s", e)
                        continue
            except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                logger.debug("자식 컨트롤 목록 조회 실패: %s", e)
            except Exception as e:
                logger.warning("자식 컨트롤 순회 중 예상치 못한 오류: %s", e)
            # Print control identifiers for debugging (only if no text found)
            if not all_texts:
                try:
                    logger.debug("확인 창 컨트롤 구조 분석 중...")
                    # 컨트롤 구조를 문자열로 캡처
                    old_stdout = sys.stdout
                    sys.stdout = mystdout = io.StringIO()
                    try:
                        confirm_window.print_control_identifiers()
                        control_info = mystdout.getvalue()
                        # 처음 500자만 로깅
                        logger.debug("컨트롤 정보: %s", control_info[:500])
                    finally:
                        sys.stdout = old_stdout
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("컨트롤 구조 분석 실패: %s", e)
                except Exception as e:
                    logger.warning("컨트롤 구조 분석 중 예상치 못한 오류: %s", e)
            result = " ".join(all_texts)
            logger.debug("상세 텍스트 수집 결과: '%s'", result)
            return result
        except Exception as e:
            logger.debug("상세 대화상자 텍스트 가져오기 실패: %s", e)
            return ""

    def check_document_flow_state(self) -> str:
        """
        현재 문서 처리 흐름 상태를 확인합니다.

        Returns:
            str: 현재 문서 처리 상태 (CONTINUE, EXIT, UNKNOWN)
        """
        try:
            # 확인 창이 존재하는지 확인
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if not confirm_window.exists():
                return DocumentFlowState.CONTINUE

            # 창의 텍스트 내용을 확인하여 상태 결정
            window_text = self.get_confirm_dialog_text()
            action = self.dialog_classifier.classify_dialog_action(window_text)

            if action == DialogAction.UNKNOWN and (
                window_text.strip() == "확인" or not window_text.strip()
            ):
                # 텍스트를 충분히 읽지 못한 경우, 더 자세히 분석
                logger.warning(
                    "대화상자 텍스트가 불완전합니다. 더 상세한 분석을 시도합니다."
                )
                detailed_text = self.get_detailed_dialog_text()
                if detailed_text:
                    logger.info("상세 텍스트 발견: '%s'", detailed_text)
                    action = self.dialog_classifier.classify_dialog_action(
                        detailed_text
                    )

                if action == DialogAction.UNKNOWN:
                    logger.warning("대화상자 내용을 판단할 수 없습니다")
                    return DocumentFlowState.UNKNOWN

            # DialogAction을 DocumentFlowState로 변환
            if action == DialogAction.EXIT:
                flow_state = DocumentFlowState.EXIT
            elif action in (
                DialogAction.CONTINUE,
                DialogAction.APPROVE,
                DialogAction.CANCEL_APPROVE,
            ):
                flow_state = DocumentFlowState.CONTINUE
            else:
                flow_state = DocumentFlowState.UNKNOWN

            # 로깅
            action_descriptions = {
                DialogAction.CONTINUE: "다음 문서 처리 대화상자 감지",
                DialogAction.EXIT: "종료 확인 대화상자 감지",
                DialogAction.APPROVE: "결재 진행 확인 대화상자 감지",
                DialogAction.CANCEL_APPROVE: "취소 결재 확인 대화상자 감지",
                DialogAction.UNKNOWN: "알 수 없는 확인 대화상자",
            }

            logger.info(action_descriptions.get(action, f"알 수 없는 액션: {action}"))
            return flow_state

        except (AttributeError, RuntimeError, ElementNotFoundError) as e:
            logger.debug("문서 흐름 상태 확인 중 예외: %s", e)
            return DocumentFlowState.CONTINUE
        except Exception as e:
            logger.warning("예상치 못한 오류: %s", e)
            return DocumentFlowState.EXIT

    @log_execution_time(logger)
    def handle_reception_confirmation(
        self, wait_for_condition_callback: callable
    ) -> None:
        """
        '문서를 접수하시겠습니까?' 확인 대화상자를 처리합니다.

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
        """
        # 더 정확한 대화상자 식별: 메시지 텍스트로 직접 확인
        reception_dialog_appeared = wait_for_condition_callback(
            lambda: (
                self.dlg.child_window(title="확인", control_type="Window") is not None
                and self.dlg.child_window(title="확인", control_type="Window").exists()
                and self.dlg.child_window(
                    title="문서를 접수하시겠습니까?", class_name="Static"
                )
                is not None
                and self.dlg.child_window(
                    title="문서를 접수하시겠습니까?", class_name="Static"
                ).exists()
            ),
            timeout=TimeoutConfig.RECEPTION_CONFIRMATION,
            interval=TimeoutConfig.CONDITION_WAIT_INTERVAL,
        )

        if reception_dialog_appeared:
            logger.info("접수 확인 대화상자 감지 - 확인 버튼 클릭")
            # 정확한 메시지가 확인되었으므로 즉시 확인 버튼 클릭
            confirm_dialog = self.dlg.child_window(title="확인", control_type="Window")
            confirm_button = confirm_dialog.child_window(
                title="확인", class_name="Button"
            )
            confirm_button.click()
            logger.debug("접수 확인 완료")
        else:
            logger.warning("접수 확인 대화상자가 나타나지 않음")

    @log_execution_time(logger)
    def handle_circulation_completion(
        self, wait_for_condition_callback: callable
    ) -> None:
        """
        '공람지정을 완료하였습니다.' 확인 대화상자를 처리합니다.

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
        """
        # 더 정확한 대화상자 식별: 메시지 텍스트로 직접 확인
        circulation_dialog_appeared = wait_for_condition_callback(
            lambda: (
                self.dlg.child_window(title="확인", control_type="Window").exists()
                and self.dlg.child_window(
                    title="공람지정을 완료하였습니다.", class_name="Static"
                ).exists()
            ),
            timeout=TimeoutConfig.CIRCULATION_COMPLETION,
            interval=TimeoutConfig.CONDITION_WAIT_INTERVAL,
        )

        if circulation_dialog_appeared:
            logger.info("공람지정 완료 대화상자 감지 - 확인 버튼 클릭")
            # 정확한 메시지가 확인되었으므로 즉시 확인 버튼 클릭
            confirm_dialog = self.dlg.child_window(title="확인", control_type="Window")
            confirm_button = confirm_dialog.child_window(
                title="확인", class_name="Button"
            )
            confirm_button.click()
            logger.debug("공람지정 완료 확인 완료")
        else:
            logger.debug("공람지정 완료 대화상자가 나타나지 않음")

    @log_execution_time(logger)
    def handle_reception_result(
        self, wait_for_condition_callback: callable, handle_confirm_callback: callable
    ) -> None:
        """
        접수 후 결과 처리 (종료 또는 다음 문서).

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
            handle_confirm_callback: 확인 대화상자 처리 콜백 함수
        """
        result_dialog_appeared = wait_for_condition_callback(
            lambda: self.dlg.child_window(title="확인", control_type="Window").exists(),
            timeout=TimeoutConfig.APPROVAL_RESULT,
        )
        if result_dialog_appeared:
            dialog_text = self.get_confirm_dialog_text()
            logger.info("접수 결과 대화상자 텍스트: '%s'", dialog_text)

            action = self.dialog_classifier.classify_dialog_action(dialog_text)
            if action == DialogAction.EXIT:
                logger.info("종료 확인 - 접수 처리 종료")
            elif action == DialogAction.CONTINUE:
                logger.info("다음 문서 처리 확인 - 계속 진행")
            else:
                logger.info("일반적인 확인 대화상자 - 기본 처리")

            handle_confirm_callback()
        else:
            logger.info("접수 결과 대화상자가 나타나지 않음 - 처리 완료")

    @log_execution_time(logger)
    def handle_approval_confirmation(
        self, wait_for_condition_callback: callable, handle_confirm_callback: callable
    ) -> None:
        """
        '결재를 진행하시겠습니까?' 확인 대화상자를 처리합니다.

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
            handle_confirm_callback: 확인 대화상자 처리 콜백 함수
        """
        # 더 정확하고 빠른 대화상자 식별: 특정 Static 텍스트로 직접 확인
        approval_dialog_appeared = wait_for_condition_callback(
            lambda: (
                self.dlg.child_window(title="확인", control_type="Window").exists()
                and self.dlg.child_window(
                    title="결재를 진행하시겠습니까?", class_name="Static"
                ).exists()
            ),
            timeout=TimeoutConfig.APPROVAL_CONFIRMATION,
            interval=TimeoutConfig.CONDITION_WAIT_INTERVAL,
        )

        if approval_dialog_appeared:
            logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
            # 정확한 메시지가 확인되었으므로 즉시 확인 버튼 클릭
            confirm_dialog = self.dlg.child_window(title="확인", control_type="Window")
            confirm_button = confirm_dialog.child_window(
                title="확인", class_name="Button"
            )
            confirm_button.click()
            logger.debug("결재 진행 확인 완료")
        else:
            # 백업: 일반적인 확인 대화상자가 있는지 확인
            general_dialog_appeared = wait_for_condition_callback(
                lambda: self.dlg.child_window(
                    title="확인", control_type="Window"
                ).exists(),
                timeout=TimeoutConfig.APPROVAL_CONFIRMATION_BACKUP,
            )
            if general_dialog_appeared:
                confirm_dialog = self.dlg.child_window(
                    title="확인", control_type="Window"
                )
                dialog_text = self.analyze_dialog_content(confirm_dialog)
                logger.info("결재 확인 대화상자 텍스트: '%s'", dialog_text)

                # 결재 진행 확인 패턴 체크
                if "결재를 진행하시겠습니까" in dialog_text:
                    logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
                    handle_confirm_callback()
                else:
                    # 기존 분류기도 사용
                    action = self.dialog_classifier.classify_dialog_action(dialog_text)
                    if action == DialogAction.APPROVE:
                        logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
                    else:
                        logger.warning("예상하지 못한 확인 대화상자: %s", dialog_text)
                    handle_confirm_callback()
            else:
                logger.info("결재 진행 확인 대화상자가 나타나지 않음")

    @log_execution_time(logger)
    def handle_approval_result(self, click_confirm_callback: callable) -> None:
        """
        결재 결과를 처리합니다 (완료 또는 다음 문서) - 초고속 최적화 버전.

        Args:
            click_confirm_callback: 확인 버튼 클릭 콜백 함수
        """
        logger.info("결재 결과 대화상자 대기 시작 - handle_approval_result() 호출됨")
        time.sleep(TimeoutConfig.MINIMAL_DELAY)

        # 초고속 대화상자 찾기
        confirm_dialog = self.find_confirm_dialog()

        if not confirm_dialog:
            logger.info("대화상자 없이도 다음 처리 계속 진행")
            return

        # 빠른 텍스트 패턴 매칭 (분석 생략하고 즉시 처리)
        dialog_text = self.get_quick_dialog_text(confirm_dialog)
        logger.info("결재 확인 대화상자 텍스트: '%s'", dialog_text)

        # 즉시 패턴 매칭으로 빠른 처리
        if (
            "다음 문서를 처리하겠습니까" in dialog_text
            or "결재문서가 완료되었습니다" in dialog_text
        ):
            logger.info("다음 문서 처리 대화상자 감지")
            click_confirm_callback(confirm_dialog)
        elif "종료하시겠습니까" in dialog_text:
            logger.info("종료 확인 대화상자 감지 - 프로세스 종료")
            click_confirm_callback(confirm_dialog)
        else:
            # 복잡한 분석 대신 기본 처리
            logger.info("기본 확인 처리")
            click_confirm_callback(confirm_dialog)
