from concurrent.futures import ThreadPoolExecutor

import appl
from appl import gen, ppl, traceable

appl.init()


@ppl
def add(x: int, y: int):
    f"{x}+{y}=?"
    return gen()


@traceable
def calc():
    return [add(x, y) for x in range(3) for y in range(3)]


@traceable
def calc_with_thread():
    with ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(add, range(9), range(9)))


@traceable
def main():
    print(f"{calc()}")
    print(f"{calc_with_thread()}")


if __name__ == "__main__":
    main()
