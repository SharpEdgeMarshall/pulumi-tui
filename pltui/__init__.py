import os

# gRPC (loaded by the Pulumi SDK) writes native log lines to stderr, which
# corrupt the TUI. This must be set before gRPC is first imported.
os.environ.setdefault("GRPC_VERBOSITY", "NONE")
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")
