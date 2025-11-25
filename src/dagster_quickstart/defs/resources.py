# dagster_sandbox/resources/impala_resource.py
import dagster as dg
from dagster import ConfigurableResource, EnvVar

class ImpalaResource(ConfigurableResource):
    host: str = EnvVar("IMPALA_HOST")
    port: int = EnvVar("IMPALA_PORT")
    user: str = EnvVar("IMPALA_USER")
    password: str = EnvVar("IMPALA_PASSWORD")
    http_path: str = EnvVar("IMPALA_HTTP_PATH")


    def get_connection(self):
        return ibis.impala.connect(
            host=self.host,
            port=int(self.port),
            user=self.user,
            password=self.password,
            use_ssl=True,
            auth_mechanism="PLAIN",
            use_http_transport=True,
            http_path=self.http_path,
        )
    
@dg.definitions
def resources():
    return dg.Definitions(resources={"database": ImpalaResource()})