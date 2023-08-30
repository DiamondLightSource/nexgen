from .command_line import version_parser


def main(args=None):
    args = version_parser.parse_args(args)


# Test with python -m nexgen
if __name__ == "__main__":
    main()