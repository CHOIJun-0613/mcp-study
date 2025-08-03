#!/usr/bin/env python3
"""
로깅 설정 모듈
환경변수를 통해 로그 레벨과 출력 방식을 설정할 수 있습니다.
"""

import os
import logging
import logging.handlers
from typing import Optional
from pathlib import Path

# 환경변수에서 로깅 설정 읽기
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_OUTPUT = os.getenv("LOG_OUTPUT", "stdout").lower()  # stdout, file, both
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/mcp-server.log")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10"))  # MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    로거를 설정하고 반환합니다.
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None이면 환경변수 사용)
    
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)
    
    # 로그 포맷터 설정
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 출력 방식에 따른 핸들러 설정
    if LOG_OUTPUT in ["stdout", "both"]:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if LOG_OUTPUT in ["file", "both"]:
        # 로그 파일 경로 설정
        if log_file is None:
            log_file = LOG_FILE_PATH
        
        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 로테이팅 파일 핸들러 설정
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_SIZE * 1024 * 1024,  # MB to bytes
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    기존 로거를 반환하거나 새로 생성합니다.
    
    Args:
        name: 로거 이름
    
    Returns:
        로거 인스턴스
    """
    return logging.getLogger(name)

# 기본 로거 설정
default_logger = setup_logger("mcp-server") 