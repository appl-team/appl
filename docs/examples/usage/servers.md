# Servers

## Configuration

You can configure the LLM servers in the `appl.yaml` file. The following is an example of the `appl.yaml` file we used in this examples:

```yaml linenums="1" title="appl.yaml (example)"
--8<-- "examples/appl.yaml"
```

## API

You need to setup your API keys or some other environment variables in the `.env` file.
The following is an example of the `.env` file we used in this examples:

```bash title=".env"
# Azure environment variables
AZURE_API_KEY = <your azure api key>
AZURE_API_BASE = <the base url of the API>
AZURE_API_VERSION = <the version of the API>
# Moonshot environment variables
MOONSHOT_API_KEY = <your moonshot api key>
```

## Local
We recommend using [SGlang Runtime (SRT)](https://github.com/sgl-project/sglang?tab=readme-ov-file#backend-sglang-runtime-srt) to serve the local LLMs, where its automatic KV cache reuse with RadixAttention can provide accelerate in many use cases.

You may use [vLLM](https://github.com/vllm-project/vllm) to host a local server, and the configuration in APPL is similar to using the SRT server.

Using Llama-2-7b-chat-hf as an example:
```bash
python -m sglang.launch_server --model-path meta-llama/Llama-2-7b-chat-hf --port 30000
```

## Example
```python linenums="1"
--8<-- "examples/usage/multiple_servers.py"
```