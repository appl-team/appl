import appl
from appl import AIRole, convo, gen, ppl, records

appl.init()


@ppl(ctx="same")  # repeat in the same context
def get_output(attempt_index: int):
    # mock response for demonstration purpose
    mock_response = "1" if attempt_index < 4 else "2"
    with AIRole():
        (res := gen(mock_response=mock_response))
    # validation, replace with your validation logic and messages
    is_valid = res == "2"
    if is_valid:
        "You guessed it!"
    else:
        "Try again!"
    # print(f"attempt = {attempt_index}")
    # print(convo())
    return is_valid, records()


@ppl(ctx="copy")  # copy to avoid modifying the original
def get_valid_gen(num_attempts: int = 5):
    messages = None
    for i in range(num_attempts):
        is_valid, messages = get_output(i)
        if is_valid:
            break
    return messages  # return the last set of messages


@ppl
def main():
    "Your task is to guess the correct number in the range 1 to 10."
    get_valid_gen()
    return convo()


print("The conversation is stored in the main function is:")
print(main())
