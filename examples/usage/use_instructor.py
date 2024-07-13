from pydantic import BaseModel

import appl
from appl import gen, ppl

appl.init()


# Define your desired output structure
class UserInfo(BaseModel):
    name: str
    age: int


@ppl
def get_user_info() -> UserInfo:
    # Extract structured data from natural language
    "John Doe is 30 years old."
    return gen(response_model=UserInfo).results


user_info = get_user_info()

print(user_info.name)
# > John Doe
print(user_info.age)
# > 30
