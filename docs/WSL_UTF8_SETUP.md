# WSL_UTF8_SETUP.md

## 문서 정보
- 제품명: Coin Lab
- 문서 목적: 전략 연구, 실시간 모니터링, 백테스트, PAPER/LIVE 실행을 하나의 제품 요구사항으로 정리한다.
- 문서 상태: Draft
- 기준 일자: 2026-03-12
- 변경 이력: [CHANGELOG_AGENT.md](./CHANGELOG_AGENT.md)

## Goal
Prevent Korean text from appearing garbled when working in WSL with Codex, VS Code, or terminal-based tools.

## What was happening
In this repository, most files are already saved as UTF-8.
The common failure mode is not file corruption, but the terminal or WSL locale reading UTF-8 text with the wrong encoding assumptions.

Typical symptoms:

- Korean text looks broken in terminal output
- Markdown files look fine in the editor but broken in shell output
- `cat`, `less`, `git diff`, or agent output shows mojibake

## Repo-level protections added
- `.editorconfig`
  Forces UTF-8 as the default file charset.
- `.gitattributes`
  Normalizes text files and line endings.
- `.vscode/settings.json`
  Forces UTF-8 in the editor and sets UTF-8 locale vars for Linux terminals.
- `scripts/wsl-utf8-env.sh`
  Quick environment bootstrap for WSL shell sessions.
- `scripts/check_utf8.py`
  Verifies repository text files decode as UTF-8.

## Recommended WSL usage
Run this once per shell session before using Codex in WSL:

```bash
source scripts/wsl-utf8-env.sh
```

To make it persistent, add this line to `~/.bashrc` or `~/.zshrc`:

```bash
source /path/to/coin-lab/scripts/wsl-utf8-env.sh
```

## Quick checks
Check locale:

```bash
locale
```

You should see UTF-8 values such as:

- `LANG=C.UTF-8`
- `LC_ALL=C.UTF-8`

Run the repository UTF-8 check:

```bash
python scripts/check_utf8.py
```

Expected result:

```text
All checked files decoded as UTF-8.
```

## Notes
- If VS Code shows Korean correctly but terminal output is broken, this is usually a locale issue, not a file issue.
- If `check_utf8.py` passes, the repository files are decodable as UTF-8.
- If a file still looks broken in one tool only, check that tool's output encoding before editing the file.
