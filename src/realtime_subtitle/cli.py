import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="realtime-subtitle", description="Command-line interface for realtime-subtitle.")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available subcommands")

    # UI subcommand
    ui_parser = subparsers.add_parser("ui", help="Launch the UI")
    ui_parser.set_defaults(func=run_ui)

    # Parse subcommand
    parse_parser = subparsers.add_parser("parse", help="Parse a file")
    parse_parser.add_argument(
        "-f", "--file", required=True, help="Path to the file to parse")
    parse_parser.add_argument(
        "-n", "--speakers", required=False, help="How many speakers are in the audio")
    parse_parser.set_defaults(func=run_parse)

    # Parse arguments
    args = parser.parse_args()

    # Call the appropriate function
    args.func(args)


def run_ui(args):
    from .ui import main as ui_main
    ui_main()


def run_parse(args):
    from .parse_audio import parse_audio
    file_path = args.file
    if args.speakers:
        speaker_num = int(args.speakers)
    else:
        speaker_num = -1
    print(f"Parsing file: {file_path}")
    parse_audio(file_path, speaker_num=speaker_num)


if __name__ == "__main__":
    main()
