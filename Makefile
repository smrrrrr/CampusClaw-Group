# 一键门禁入口；实现见 scripts/check.py（Windows 无 make 时直接运行该脚本）
.PHONY: check

check:
	backend/.venv/bin/python scripts/check.py
