# together-skills-sdk-check

I wanted to know whether the Python scripts in [togethercomputer/skills](https://github.com/togethercomputer/skills) actually run on the current `together` SDK, since `together` 3.0.0 shipped on Oct 22 2026 and changed a lot of client paths.

`check_sdk_calls.py` is a small static checker. For every script that creates `Together(...)` or `AsyncTogether(...)`, it walks each call made through that client (`client.a.b.c(...)`), checks that the attribute path exists on a real client object from the installed SDK, and checks every keyword argument against the method signature. It makes no network calls and needs no API key.

## Results

Skills repo at `main` = `a00c1b3` (Nov 2 2026). 31 scripts, 27 create a client, 158 client calls checked.

| SDK | Broken calls | Where |
|---|---|---|
| `together` 3.0.0 | 33 in 6 scripts | `dedicated-model-inference/deploy_model.py`, `upload_custom_model.py` (`client.beta.models` / `client.beta.endpoints` no longer exist), `gpu-clusters/manage_cluster.py`, `manage_storage.py` (`client.beta.clusters`), `video/generate_video.py`, `image_to_video.py` (`reference_images=` / `frame_images=` moved under `media=`) |
| `together` 2.42.0 | 40 in 5 scripts | every `fine-tuning/*` script, which was already ported to the 3.x `client.endpoints.deployments` / `client.models.configs` surface |

So on `main` there is no single SDK version where every script's calls line up. Full output is in `results-main-together-3.0.0.txt` and `results-main-together-2.42.0.txt`.

I also merged the scripts from open PR #82 (`8f09a22`, the 3.x port) onto `main` and re-ran it: 0 broken calls on 3.0.0 out of 159 (`results-main-plus-pr82-together-3.0.0.txt`). The Python files merge cleanly; a few markdown files conflict.

One of the 3.0.0 findings, confirmed at runtime with no API key:

```
>>> Together(api_key="x").videos.create(prompt="x", model="m", reference_images=["a"])
TypeError: VideosResource.create() got an unexpected keyword argument 'reference_images'
```

## Run it

```bash
uv venv && uv pip install "together==3.0.0"
git clone https://github.com/togethercomputer/skills
.venv/bin/python check_sdk_calls.py skills/skills
```

## Limits

- Only calls made through a variable assigned from `Together(...)` / `AsyncTogether(...)` are checked. Calls on returned objects (for example `job.status`) and argument types are not.
- Methods that accept `**kwargs` skip the keyword check.
- It checks that a call is well-formed for the SDK, not that the request succeeds against the live API.
