# Why use APPL?

!!! warning "This page is under construction"
    This page is under construction.

The common practice for interacting with Large Language Models (LLMs) 
creating prompts is to write them as static text. This might be sufficient for simple prompts, but it can become cumbersome and error-prone when dealing with complex or dynamic prompts. APPL provides a code-based approach to prompt generation, which offers several advantages over static text-based methods.

!!! question "Why using code to represent prompts?"
    1. **Dynamic Content Creation**: The code-based approach allows for dynamic generation of prompts based on variables or conditions. This can make it easier to generate customized prompts based on specific inputs, without manually writing each prompt.

    2. **Reusability**: Code can be reused across different contexts with slight modifications. Functions can be called with different arguments to generate various prompts without duplicating the text for each one.

    3. **Modular Structure**: By dividing the prompt into distinct components, you can easily modify or extend parts of the prompt without affecting the whole structure. This modular design enhances maintainability and scalability.

    4. **Error Checking and Validation**: When prompts are generated through code, you can include error checking and validation to ensure the resulting text meets certain criteria or standards, potentially reducing mistakes or inconsistencies in the prompt creation process.
