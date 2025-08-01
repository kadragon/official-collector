#!/usr/bin/env python3
"""
AI-friendly Debug Helper

이 모듈은 AI가 창 구조를 분석하고 디버깅하기 위한 프로그래매틱 인터페이스를 제공합니다.
"""

import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
import sys
import os

# 프로젝트 루트 기준으로 경로 설정
project_root = Path(__file__).parent.parent.parent  # utils -> src -> project_root
sys.path.append(str(project_root / 'src'))
from debug_window_structure import WindowStructureDebugger

logger = logging.getLogger(__name__)


class AIDebugHelper:
    """AI가 사용하기 위한 디버깅 헬퍼 클래스"""
    
    def __init__(self):
        self.debugger = None
        
    def quick_window_analysis(self, app_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        빠른 창 구조 분석
        
        Args:
            app_patterns: 검색할 애플리케이션 패턴 리스트
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Non-interactive debugger 생성
            self.debugger = WindowStructureDebugger(
                app_title_patterns=app_patterns,
                interactive=False
            )
            
            # 애플리케이션 연결 시도
            if not self.debugger.connect_to_app():
                return {
                    'success': False,
                    'error': 'Failed to connect to application',
                    'connected_app': None,
                    'window_structure': None
                }
            
            # 창 구조 추출
            window_structure = self.debugger.print_window_structure(save_to_file=True)
            
            return {
                'success': True,
                'connected_app': self.debugger.dlg.window_text() if self.debugger.dlg else None,
                'window_structure': window_structure,
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Quick window analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'connected_app': None,
                'window_structure': None
            }
    
    def monitor_dialogs_programmatic(self, duration: float = 10.0, interval: float = 0.5) -> List[Dict[str, Any]]:
        """
        프로그래매틱 대화상자 모니터링
        
        Args:
            duration: 모니터링 지속 시간 (초)
            interval: 체크 간격 (초)
            
        Returns:
            List of dialog information detected during monitoring
        """
        if not self.debugger or not self.debugger.dlg:
            logger.error("No active debugger connection. Call quick_window_analysis first.")
            return []
        
        dialogs_found = []
        start_time = datetime.now()
        
        logger.info(f"Starting programmatic dialog monitoring for {duration}s")
        
        import time
        monitoring_start = time.time()
        iteration = 0
        
        while time.time() - monitoring_start < duration:
            iteration += 1
            
            try:
                # 대화상자 찾기
                dialogs = self.debugger._find_confirm_dialogs()
                
                if dialogs:
                    for dialog in dialogs:
                        dialog_info = self._analyze_dialog(dialog, iteration)
                        dialogs_found.append(dialog_info)
                        logger.info(f"Dialog detected: {dialog_info['title']}")
                
            except Exception as e:
                logger.debug(f"Error during dialog monitoring iteration {iteration}: {e}")
            
            time.sleep(interval)
        
        logger.info(f"Dialog monitoring completed. Found {len(dialogs_found)} dialog instances.")
        return dialogs_found
    
    def _analyze_dialog(self, dialog, iteration: int) -> Dict[str, Any]:
        """
        대화상자 분석
        
        Args:
            dialog: 분석할 대화상자 객체
            iteration: 모니터링 반복 횟수
            
        Returns:
            Dict containing dialog analysis
        """
        try:
            dialog_info = {
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'title': getattr(dialog, 'window_text', lambda: 'Unknown')(),
                'class_name': getattr(dialog, 'class_name', lambda: 'Unknown')(),
                'rect': None,
                'text_content': None,
                'controls': []
            }
            
            # 위치 정보 추출
            try:
                rect = dialog.rectangle()
                dialog_info['rect'] = {
                    'left': rect.left,
                    'top': rect.top,
                    'right': rect.right,
                    'bottom': rect.bottom
                }
            except:
                pass
            
            # 텍스트 내용 추출
            try:
                dialog_info['text_content'] = self._get_dialog_text_safe(dialog)
            except:
                pass
            
            # 하위 컨트롤 정보 추출
            try:
                children = dialog.children()
                dialog_info['controls'] = [
                    {
                        'control_type': getattr(child, 'element_info', {}).get('control_type', 'Unknown'),
                        'title': getattr(child, 'window_text', lambda: '')(),
                        'class_name': getattr(child, 'class_name', lambda: '')()
                    }
                    for child in children[:5]  # 처음 5개만
                ]
            except:
                pass
            
            return dialog_info
            
        except Exception as e:
            logger.error(f"Failed to analyze dialog: {e}")
            return {
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _get_dialog_text_safe(self, dialog) -> str:
        """
        안전한 대화상자 텍스트 추출
        
        Args:
            dialog: 대화상자 객체
            
        Returns:
            str: 추출된 텍스트
        """
        text_methods = [
            lambda: dialog.window_text(),
            lambda: dialog.child_window(control_type="Text").window_text(),
            lambda: dialog.child_window(control_type="Static").window_text(),
        ]
        
        for method in text_methods:
            try:
                text = method()
                if text and text.strip():
                    return text
            except:
                continue
        
        return ""
    
    def find_circulation_completion_dialog(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        공람지정 완료 대화상자 찾기
        
        Args:
            timeout: 최대 대기 시간
            
        Returns:
            Dialog information if found, None otherwise
        """
        if not self.debugger or not self.debugger.dlg:
            logger.error("No active debugger connection.")
            return None
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                dialogs = self.debugger._find_confirm_dialogs()
                
                for dialog in dialogs:
                    text_content = self._get_dialog_text_safe(dialog)
                    
                    # 공람지정 관련 대화상자 확인
                    if any(keyword in text_content for keyword in ["공람지정", "완료", "확인"]):
                        dialog_info = self._analyze_dialog(dialog, 0)
                        dialog_info['is_circulation_dialog'] = True
                        logger.info(f"Found circulation completion dialog: {text_content[:50]}")
                        return dialog_info
                
            except Exception as e:
                logger.debug(f"Error searching for circulation dialog: {e}")
            
            time.sleep(0.1)
        
        logger.info("No circulation completion dialog found within timeout")
        return None


def create_ai_debug_helper() -> AIDebugHelper:
    """AI 디버그 헬퍼 생성 함수"""
    return AIDebugHelper()


def quick_debug_current_window() -> Dict[str, Any]:
    """
    현재 창 빠른 디버깅 (편의 함수)
    
    Returns:
        Dict containing debug results
    """
    helper = AIDebugHelper()
    return helper.quick_window_analysis()


def monitor_for_circulation_dialogs(duration: float = 10.0) -> List[Dict[str, Any]]:
    """
    공람지정 관련 대화상자 모니터링 (편의 함수)
    
    Args:
        duration: 모니터링 지속 시간
        
    Returns:
        List of detected dialogs
    """
    helper = AIDebugHelper()
    
    # 연결 시도
    analysis = helper.quick_window_analysis()
    if not analysis['success']:
        logger.error("Failed to connect to application for monitoring")
        return []
    
    # 모니터링 실행
    return helper.monitor_dialogs_programmatic(duration=duration)