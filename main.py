import os
import anthropic
import openai
from textwrap import dedent
import subprocess
import json
import readline

def prompt_anthropic(prompt: str) -> str:
    c = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    resp = c.completion(
        prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        model="claude-v1",
        max_tokens_to_sample=1000,
    )
    return resp['completion']

def prompt_openai(prompt):
    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {"role": "system", "content": "You help generate bash commands from natural language"},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=1000,
    )
    return response.choices[0].message.content

def list_command_line_tools():
    path = os.environ['PATH']
    path_dirs = path.split(os.pathsep)

    commands = set()
    for path_dir in path_dirs:
        if os.path.exists(path_dir):
            for item in os.listdir(path_dir):
                item_path = os.path.join(path_dir, item)
                if os.access(item_path, os.X_OK) and os.path.isfile(item_path):
                    commands.add(item)

    return commands

def main_prompt(task: str) -> str:
    prompt = dedent(
        f"""
I want you to assist with generating a bash command to accomplish a task.

You can use standard command line tools that are installed on a mac.

The task is: {task}

I want you to output the exact command you would run.
Do not use the shuf command.
If using python, use python3.

Then, after doing so, I want you to include it as JSON wrapped in <result></result> tags, like the the following format: <result>{{ "command" :"<your command here>"}}</result>
        """
    )
    raw = prompt_anthropic(prompt)
    if "<result>" not in raw or "</result" not in raw:
        print("ERROR: Result not returned by LLM")
        return None
    json_str = raw.split("<result>")[1].split("</result>")[0]
    output = json.loads(json_str)
    if "command" not in output:
        print("ERROR: Command not returned by LLM")
        return None
    return output["command"]

def llm_output_prompt(command_run: str, output: SyntaxError) -> str:
    prompt = dedent(
        f"""
        I want you to translate the result of a UNIX command into simple natural language to make it easy for a user to understand.

        The command that was run was {command_run}.

        The output was {output}.

        I want you to the translation as JSON wrapped in <result></result> tags, like the the following format: <result>{{ "translation" :"<your translation here>"}}</result>
        The result will be parsed by python's json.loads, so don't use any characters like \\ which would be hard to parse.
        """
    )
    raw =  prompt_anthropic(prompt)
    if "<result>" not in raw or "</result>" not in raw:
        print("ERROR: result not returned by LLM")
        return None
    json_str = raw.split("<result>")[1].split("</result>")[0]
    output = json.loads(json_str)
    if "translation" not in output:
        print("ERROR: translation not returned by LLM")
        return None
    return output["translation"]

def loop():
    while True:
        try:
            command = input("$ ")

            if command == "exit":
                break
            else:
                new_command = command
                if command.startswith("!"):
                    new_command = command[1:].strip()
                llm_generated_command = main_prompt(new_command)
                if llm_generated_command is None:
                    continue
                process = subprocess.Popen(llm_generated_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = process.communicate()

                if output:
                    if command.startswith("!"):
                        print(llm_output_prompt(command, output.decode('utf-8')))
                    else:
                        print(output.decode('utf-8'))
                if error:
                    print(error.decode('utf-8'))

        except Exception as e:
            print(f"Error: {e}")

def main():
    loop()

if __name__ == "__main__":
    main()
