"""One structured-output call to Claude, shared by clean and post."""
import json
import sys

from gdvideo.config import CLAUDE_EFFORT, CLAUDE_MODEL


def ask_json(prompt, schema, task):
    """Send prompt, get back a dict matching schema. Exits with a readable message on failure."""
    import anthropic

    print(f"{task} with {CLAUDE_MODEL}...", file=sys.stderr)
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": CLAUDE_EFFORT, "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
    except (anthropic.AuthenticationError, TypeError) as e:
        # TypeError: the SDK found no credentials at all
        if isinstance(e, TypeError) and "authentication" not in str(e):
            raise
        sys.exit("Anthropic API credentials are missing or invalid. Set ANTHROPIC_API_KEY (see README).")
    except anthropic.APIConnectionError as e:
        sys.exit(f"Could not reach the Anthropic API: {e}")
    except anthropic.APIStatusError as e:
        sys.exit(f"Anthropic API error {e.status_code}: {e.message}")

    if response.stop_reason == "refusal":
        sys.exit(f"Claude declined the request ({task}). Try again or write it by hand.")
    if response.stop_reason == "max_tokens":
        sys.exit(f"Claude's answer was cut off (max_tokens) ({task}). Try again.")
    print(f"  tokens in/out: {response.usage.input_tokens}/{response.usage.output_tokens}", file=sys.stderr)
    return json.loads(next(b.text for b in response.content if b.type == "text"))
