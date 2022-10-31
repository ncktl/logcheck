import argparse
import logging
from pathlib import Path

from logcheck.dtos import Settings
from logcheck.logcheck import supported_languages
from logcheck.processing import extract
from logcheck.utils import overwrite
from .config import suffix

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("LogCheck")

if __name__ == "__main__":
    # Handle arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. LogCheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output file.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages, default="python",
                            help="Specify the language. Default: python")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode.")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Also extract the context when in extraction mode")
    arg_parser.add_argument("-z", "--zhenhao", action="store_true",
                            help="Mimic Zhenhao et al. approach when in extraction mode")
    args = arg_parser.parse_args()

    # Check arguments
    if not args.path.exists():
        arg_parser.error("Path does not exist.")
    # Detect batch mode
    if args.path.is_dir():
        batch = True
    elif args.path.is_file():
        batch = False
    else:
        arg_parser.error("Path is neither file nor directory.")

    # File overwrite dialog
    if args.output and args.output.is_file() and not args.force:
        overwrite()

    settings = Settings(path=args.path,
                        output=args.output,
                        language=args.language,
                        debug=args.debug,
                        alt=args.alt,
                        zhenhao=args.zhenhao)

    if batch:
        files = list(settings.path.glob(f"**/*{suffix[settings.language]}"))
    else:
        files = [args.path]

    if args.extract:
        extract(files, settings)
