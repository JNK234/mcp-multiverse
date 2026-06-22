# ABOUTME: Format codecs — convert bytes <-> structured data for each config file format.
# ABOUTME: Codecs are tool-agnostic; engines apply per-tool field mappings on top of them.
from mcpx.codecs.base import Codec, codec_for

__all__ = ["Codec", "codec_for"]
