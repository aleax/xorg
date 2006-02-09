SOURCE_VERSION=@SOURCE_VERSION@

# Use special abnormal exit codes so that problems with this library are more
# easily tracked down.
SHELL_LIB_INTERNAL_ERROR=86
SHELL_LIB_THROWN_ERROR=74
SHELL_LIB_USAGE_ERROR=99

THIS_PACKAGE=${THIS_PACKAGE:-"(unknown package)"}
THIS_SCRIPT=${THIS_SCRIPT:-"(unknown script)"}

ARCHITECTURE="$(dpkg --print-installation-architecture)"

if laptop-detect >/dev/null; then
    LAPTOP=true
fi

if [ "$1" = "reconfigure" ] || [ -n "$DEBCONF_RECONFIGURE" ]; then
  RECONFIGURE="true"
else
  RECONFIGURE=
fi

if ([ "$1" = "install" ] || [ "$1" = "configure" ]) && [ -z "$2" ]; then
  FIRSTINST="yes"
fi

if [ -z "$RECONFIGURE" ] && [ -z "$FIRSTINST" ]; then
  UPGRADE="yes"
fi

trap "message;\
      message \"Received signal.  Aborting $THIS_PACKAGE package $THIS_SCRIPT script.\";\
      message;\
      exit 1" HUP INT QUIT TERM

reject_nondigits () {
  # syntax: reject_nondigits [ operand ... ]
  #
  # scan operands (typically shell variables whose values cannot be trusted) for
  # characters other than decimal digits and barf if any are found
  while [ -n "$1" ]; do
    # does the operand contain anything but digits?
    if ! expr "$1" : "[[:digit:]]\+$" > /dev/null 2>&1; then
      # can't use die(), because it wraps message() which wraps this function
      echo "$THIS_PACKAGE $THIS_SCRIPT error: reject_nondigits() encountered" \
           "possibly malicious garbage \"$1\"" >&2
      exit $SHELL_LIB_THROWN_ERROR
    fi
    shift
  done
}

# Query the terminal to establish a default number of columns to use for
# displaying messages to the user.  This is used only as a fallback in the
# event the COLUMNS variable is not set.  ($COLUMNS can react to SIGWINCH while
# the script is running, and this cannot, only being calculated once.)
DEFCOLUMNS=$(stty size 2> /dev/null | awk '{print $2}') || true
if ! expr "$DEFCOLUMNS" : "[[:digit:]]\+$" > /dev/null 2>&1; then
  DEFCOLUMNS=80
fi

message () {
  # pretty-print messages of arbitrary length
  reject_nondigits "$COLUMNS"
  echo "$*" | fmt -t -w ${COLUMNS:-$DEFCOLUMNS} >&2
}

observe () {
  # syntax: observe message ...
  #
  # issue observational message suitable for logging someday when support for
  # it exists in dpkg
  if [ -n "$DEBUG_XORG_PACKAGE" ]; then
    message "$THIS_PACKAGE $THIS_SCRIPT note: $*"
  fi
}

warn () {
  # syntax: warn message ...
  #
  # issue warning message suitable for logging someday when support for
  # it exists in dpkg; also send to standard error
  message "$THIS_PACKAGE $THIS_SCRIPT warning: $*"
}

die () {
  # syntax: die message ...
  #
  # exit script with error message
  message "$THIS_PACKAGE $THIS_SCRIPT error: $*"
  exit $SHELL_LIB_THROWN_ERROR
}

internal_error () {
  # exit script with error; essentially a "THIS SHOULD NEVER HAPPEN" message
  message "$THIS_PACKAGE $THIS_SCRIPT internal error: $*"
  exit $SHELL_LIB_INTERNAL_ERROR
}

usage_error () {
  message "$THIS_PACKAGE $THIS_SCRIPT usage error: $*"
  exit $SHELL_LIB_USAGE_ERROR
}

run () {
  # syntax: run command [ argument ... ]
  #
  # Run specified command with optional arguments and report its exit status.
  # Useful for commands whose exit status may be nonzero, but still acceptable,
  # or commands whose failure is not fatal to us.
  #
  # NOTE: Do *not* use this function with db_get or db_metaget commands; in
  # those cases the return value of the debconf command *must* be checked
  # before the string returned by debconf is used for anything.

  # validate arguments
  if [ $# -lt 1 ]; then
    usage_error "run() called with wrong number of arguments; expected at" \
                "least 1, got $#"
    exit $SHELL_LIB_USAGE_ERROR
  fi

  "$@" || _retval=$?

  if [ ${_retval:-0} -ne 0 ]; then
    observe "command \"$*\" exited with status $_retval"
  fi
}
