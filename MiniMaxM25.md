# Code Review - Pocket TTS

## Executive Summary

Overall this is a well-designed, production-ready TTS system with clean architecture. Key strengths include proper encapsulation, streaming support, and OpenAI compatibility. Main concerns are around thread safety, lack of rate limiting, and limited test coverage.

---

## Strengths

1. **Well-structured architecture**: Clean separation between FlowLM, Mimi codec, and TTSModel
2. **Strong public API**: Only `TTSModel` is exported, with proper encapsulation
3. **Streaming support**: Good multithreaded implementation for parallel generation/decoding
4. **Comprehensive CLI**: Both `generate` and `serve` commands with many options
5. **OpenAI compatibility**: Well-implemented `/v1/audio/speech` endpoint

---

## Issues Found

### Critical

#### 1. Thread Safety Not Enforced
- **Location**: `pocket_tts/models/tts_model.py:379`
- **Issue**: The docstrings state "NOT thread-safe" but this is only documented, not enforced. Multiple concurrent calls could corrupt state.
- **Recommendation**: Add thread locking or raise exception if concurrent access detected

#### 2. No Rate Limiting
- **Location**: `pocket_tts/main.py:305`
- **Issue**: The `/v1/audio/speech` endpoint has no rate limiting, making it vulnerable to abuse
- **Recommendation**: Add rate limiting middleware (e.g., `slowapi`)

### High Priority

#### 3. Global Mutable State
- **Location**: `pocket_tts/main.py:152-153`
- **Issue**:
```python
tts_model: TTSModel | None = None
global_model_state = None
```
This global state makes the server mode non-reentrant and not concurrent-safe.
- **Recommendation**: Use class-based server with proper instance management

#### 4. Missing Input Validation
- **Location**: `pocket_tts/main.py:264-275`
- **Issue**: The server validates `voice_url` starts with protocols but doesn't validate path traversal or file existence properly before processing.
- **Recommendation**: Add stricter validation for file paths and URLs

#### 5. Potential Memory Leak
- **Location**: `pocket_tts/models/tts_model.py:667-671`
- **Issue**: The `@lru_cache(maxsize=2)` on `_cached_get_state_for_audio_prompt` caches audio state but there's no cache invalidation mechanism when the model is garbage collected.
- **Recommendation**: Add cache clearing method or use weak references

### Medium Priority

#### 6. Hardcoded Magic Numbers
- **Location**: `pocket_tts/models/tts_model.py:776-778`
- **Issue**:
```python
_TOKENS_PER_SECOND_ESTIMATE = 3.0
_GEN_SECONDS_PADDING = 2.0
```
These should be configurable parameters.
- **Recommendation**: Move to configuration or constructor parameters

#### 7. Missing Error Handling
- **Location**: `pocket_tts/main.py:369-385`
- **Issue**: In `generate_audio()`, if threading fails silently, `thread.join()` could hang indefinitely without a timeout.
- **Recommendation**: Add timeout to thread join calls

#### 8. Inconsistent Type Hints
- **Location**: `pocket_tts/models/flow_lm.py:16`
- **Issue**:
```python
FlowNet2 = Callable[[torch.Tensor, torch.Tensor, torch.Tensor], torch.Tensor]
```
Should use `beartype.typing` since `Callable` from builtins has different behavior.
- **Recommendation**: Import from `beartype.typing` instead

#### 9. API Keys Stored in Plain Text
- **Location**: `pocket_tts/main.py:81`
- **Issue**:
```python
API_KEYS_FILE.write_text(json.dumps({"keys": keys}))
```
API keys are stored without encryption.
- **Recommendation**: Add encryption for stored API keys

### Low Priority

#### 10. Test Coverage Gaps
- **Location**: `tests/test_python_api.py`
- **Issue**: Only 27 lines testing public API - no tests for edge cases (empty text, very long text), error conditions, CLI integration tests, or streaming behavior
- **Recommendation**: Add comprehensive test suite

#### 11. Duplicate Code
- **Location**: `pocket_tts/models/tts_model.py`
- **Issue**: Duplicate code exists in `generate_audio_stream` and `_generate_audio_stream_short_text`
- **Recommendation**: Refactor to eliminate duplication

#### 12. Unused Import
- **Location**: `pocket_tts/main.py:15`
- **Issue**: `base64` imported but also used (actually used, this is fine)
- **Recommendation**: N/A

#### 13. Inconsistent Logging Levels
- **Location**: Throughout codebase
- **Issue**: Mix of `logger.info`, `logger.warning`, `logging.warning`
- **Recommendation**: Standardize logging levels

#### 14. No Connection Pooling
- **Location**: `pocket_tts/utils/weights_loading.py`
- **Issue**: No connection pooling for HuggingFace downloads
- **Recommendation**: Add connection pooling for repeated downloads

---

## Recommendations Summary

1. **Add proper thread locking** or document that server mode is single-request only
2. **Add rate limiting middleware** (e.g., `slowapi`)
3. **Add more comprehensive tests**
4. **Make hardcoded values configurable**
5. **Consider adding encryption** for API keys storage
6. **Add input validation** for file paths and URLs
7. **Use weak references** for LRU cache or add cache invalidation
8. **Add timeouts** to thread join calls

---

## Testing Recommendations

The test suite should cover:

1. Edge cases:
   - Empty text input
   - Very long text input (>4096 chars)
   - Special characters in text
   - Unicode text

2. Error conditions:
   - Invalid voice files
   - Network failures during download
   - Model loading failures

3. Integration tests:
   - CLI generate command
   - CLI serve command (with proper cleanup)
   - HTTP API endpoints

4. Streaming tests:
   - Verify chunking behavior
   - Verify early termination
   - Verify error propagation

---

## Security Considerations

1. **Rate limiting**: Add per-client rate limits
2. **API key encryption**: Encrypt keys at rest
3. **Input validation**: Validate all user inputs
4. **Path traversal**: Prevent directory traversal attacks
5. **Timeout handling**: Prevent indefinite hangs