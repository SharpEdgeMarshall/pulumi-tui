import pulumi


class Service(pulumi.ComponentResource):
    def __init__(self, name: str, parent: pulumi.Resource, replicas: int):
        super().__init__(
            "pltui:demo:Service",
            name,
            {"replicas": replicas},
            pulumi.ResourceOptions(parent=parent),
        )
        for index in range(replicas):
            endpoint = pulumi.ComponentResource(
                "pltui:demo:Endpoint",
                f"{name}-endpoint-{index + 1}",
                {"port": 8000 + index},
                pulumi.ResourceOptions(parent=self),
            )
            endpoint.register_outputs({"url": f"http://localhost:{8000 + index}"})
        self.register_outputs({"replicas": replicas, "status": "ready"})


stack = pulumi.get_stack()
replicas = 5 if stack == "dev" else 1
application = pulumi.ComponentResource("pltui:demo:Application", f"{stack}-application")
Service(f"{stack}-api", application, replicas)
Service(f"{stack}-worker", application, replicas)
application.register_outputs({"environment": stack, "services": 2})
pulumi.export("environment", stack)
