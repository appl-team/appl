# Servers

APPL manages various LM backends as servers, where each server contains a set of configurations, such as the model name, base url, and default parameters.

## Generation Parameters
The parameters used in the `gen` function to interact with the LM servers are unified into the OpenAI format, which is supported by the [`litellm`](https://github.com/BerriAI/litellm) package.

See [the documentation of `litellm.completion`](https://docs.litellm.ai/docs/completion/input#optional-fields) for the full list of parameters, where the required parameters are managed by APPL:

- `model`: configured in the server settings.
- `messages`: the full conversation (a list of messages) stored in the context when the `gen` function is called.

## Server Configurations

The basic servers are configured as follows:
```yaml
servers:
  default: gpt35-turbo
  gpt35-turbo: # the name of the server, should avoid using '.' in the name
    model: gpt-3.5-turbo # the model name
  gpt4-turbo:
    model: gpt-4-turbo
  gpt4o:
    model: gpt-4o
```

You may specify another server of `gpt-3.5-turbo` with default temperature to be `0.0` in the [`appl.yaml` file](../../setup.md#override-configs):
```yaml
servers:
  # default: gpt35-turbo-temp0  # (1)
  gpt35-turbo-temp0: # (2)
    model: gpt-3.5-turbo
    temperature: 0.0 # (3)
```

1. you may set the default server here, so you don't need to specify the server name in the `gen` function.
2. Then when you call `gen("gpt35-turbo-temp0")`, the default temperature will be `0.0`.
3. You could still override the temperature by specifying it in the `gen` function.

We provide examples of configurations for different servers in [our setup guide](../../setup.md#override-configs). See also the list of [available models in `litellm`](https://docs.litellm.ai/docs/providers).


## Multiple Servers Example
In the following, we provide a complete example for using multiple servers in different `gen` calls. The used servers are configured in [this example](../../setup.md#override-configs).

```python linenums="1"
--8<-- "examples/usage/multiple_servers.py"
```
