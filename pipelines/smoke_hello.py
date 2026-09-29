"""Minimal smoke pipeline for RHOAI Step 9."""
from kfp import dsl, compiler


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-311:latest")
def say_hello(name: str = "muffin") -> str:
    msg = f"hello {name} from chihuahua-vs-muffin lab"
    print(msg)
    return msg


@dsl.pipeline(name="lab-smoke-hello", description="Step 9 smoke: one print task")
def lab_smoke_hello(name: str = "muffin"):
    say_hello(name=name)


if __name__ == "__main__":
    compiler.Compiler().compile(lab_smoke_hello, "pipelines/lab_smoke_hello.yaml")
    print("wrote pipelines/lab_smoke_hello.yaml")
