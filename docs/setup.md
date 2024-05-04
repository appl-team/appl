# Setup Guide
You need to set up API keys or your own LLM backends to interact with LLMs.

## Setup Environment Variables

### Using Dotenv (Recommended)
We recommended you to store all your environment variables, including API keys, in a `.env` file in the root directory of your project. This file should be added to your `.gitignore` file to prevent it from being committed to your repository.

Using the `python-dotenv` package, APPL will automatically search for the `.env`, starting from the file you call `appl.init`, and load the environment variables into the current environment.

For example, you can create a `.env` file with the following content to specify your OpenAI API key:

```bash title=".env"
OPENAI_API_KEY=<your openai api key>
```

### Export or Shell Configuration
Alterantively, you can export the environment variables directly in your terminal, or add them to your shell configuration file (e.g., `.bashrc`, `.zshrc`). For example:
```bash
export OPENAI_API_KEY=<your openai api key>
```

## Setup APPL Configuration
[`default_configs.yaml`](https://github.com/appl-team/appl/blob/main/src/appl/default_configs.yaml) contains the default configurations for APPL. You can override these configurations by creating a `appl.yaml` file in the root directory of your project.

```yaml title="default_configs.yaml" linenums="1"
--8<-- "src/appl/default_configs.yaml"
```

## Setup LLMs

### LLM APIs
APPL uses [litellm](https://docs.litellm.ai/) to support various LLM APIs using the OpenAI format.

Please refer to the [list of supported providers](https://docs.litellm.ai/docs/providers). You need to setup the corresponding API keys for the LLM backend you want to use in environment variables and specify corresponding configurations in `appl.yaml`.

For more details, please refer to the [examples](./examples/usage/servers.md#api).

### Local LLMs
We recommend using [SGlang Runtime (SRT)](https://github.com/sgl-project/sglang?tab=readme-ov-file#backend-sglang-runtime-srt) to serve the local LLMs, which is fast and supports the regex constraints. You can install it following [the official guide](https://github.com/sgl-project/sglang?tab=readme-ov-file#install) and [our complementary guide](install.md#install-sglang-optional).

To serve local LLMs, please following [the official guide](https://github.com/sgl-project/sglang?tab=readme-ov-file#backend-sglang-runtime-srt).

For more details, please refer to the [examples](./examples/usage/servers.md#local).

## Setup Tracing

### APPL Tracing
You can enable APPL tracing by overriding the `tracing` configuration to `true` in `appl.yaml`.
```yaml title="appl.yaml"
settings:
  tracing:
    enabled: true
```

To resume from a previous trace, you can specify the `APPL_RESUME_TRACE` environment variable with the path to the trace file.

### LangSmith
To enable [LangSmith](https://docs.smith.langchain.com/) tracing, you need to to [obtain your API key](https://smith.langchain.com/settings) from LangSmith and add the following environment variables to your `.env` file:

```bash title=".env"
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your api key>
# [Optional] specify the project name
# LANGCHAIN_PROJECT=<your project name>
```
