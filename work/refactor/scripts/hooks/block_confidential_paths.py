import os
import sys

CONF_PREFIX = os.path.join("AuraIA IDE Vision and Roadmap", "").replace("\\", "/")


def main(argv: list[str]) -> int:
    # pre-commit passes the staged file paths as args (relative paths)
    blocked = [p for p in argv if p.replace("\\", "/").startswith(CONF_PREFIX)]
    if blocked:
        sys.stderr.write(
            "Confidential files detected in commit:\n  - "
            + "\n  - ".join(blocked)
            + "\n\nCommit blocked. Remove these files from the commit.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
