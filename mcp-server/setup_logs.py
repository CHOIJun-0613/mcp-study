#!/usr/bin/env python3
"""
로그 디렉토리 설정 스크립트
"""

import os
from pathlib import Path

def setup_logs():
    """로그 디렉토리를 생성합니다."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # .gitkeep 파일 생성 (빈 디렉토리도 git에 포함되도록)
    gitkeep_file = log_dir / ".gitkeep"
    gitkeep_file.touch(exist_ok=True)
    
    print(f"로그 디렉토리가 생성되었습니다: {log_dir.absolute()}")
    print("로그 파일은 logs/ 디렉토리에 저장됩니다.")

if __name__ == "__main__":
    setup_logs() 