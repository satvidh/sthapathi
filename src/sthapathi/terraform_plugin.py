import plugin


class TerraformPlugin(plugin.Plugin):
    class Error(plugin.Plugin.Error):
        def __init__(self, msg):
            super(TerraformPlugin.Error, self).__init__(msg)

    def __init__(self):
        """
        Constructor
        """
        super(TerraformPlugin, self).__init__()

    def generate_target_configuration(self, provider, component, **kwargs):
        """
        Generates the terraform configuration based on the sthapathi configuration.
        :param component: The component this configuration belongs to.
        :param provider: The provider for which to generate the target configuration
        :param kwargs: Arguments expected to generate the target configuration.
        """
        import json
        if "catalog_path" not in kwargs:
            raise TerraformPlugin.Error("catalog_path is required")

        if "configuration_reader" not in kwargs:
            raise TerraformPlugin.Error("configuration_reader is required")

        parameter_groups = kwargs.get("parameter_groups", [
            {
                "default": {}
            }
        ])

        catalog = self.__load_catalog(kwargs["catalog_path"])

        if provider not in catalog:
            raise TerraformPlugin.Error("{provider} not found in catalog named {catalog_name}".format(
                provider=provider,
                catalog_name=catalog["name"]
            ))

        configuration_reader = kwargs["configuration_reader"]

        target_configuration = {}
        self.__add_provider_and_backend(target_configuration, provider, component)

        modules = {}
        variables = {}

        for element in configuration_reader.read():
            if "module" in element:
                module_configuration = self.__create_module_configuration(element, catalog["name"],
                                                                          catalog[provider], parameter_groups)
                modules.update(module_configuration)
            elif "variable" in element:
                variables.update({
                    element["variable"]: {}
                })
            else:
                raise TerraformPlugin.Error("Unknown element {element}".format(
                    element=json.dumps(element)
                ))

        for parameter_group_name, parameter_group in parameter_groups.iteritems():
            for parameter in parameter_group["variables"]:
                variables.update({
                    parameter: {}
                })

        target_configuration.update({
            "module": modules,
            "variable": variables
        })

        return target_configuration

    @staticmethod
    def __load_catalog(catalog_path):
        import yaml
        with open(catalog_path, 'r') as stream:
            return yaml.load(stream)

    @staticmethod
    def __add_provider_and_backend(target_configuration, provider, component):
        terraform = {
            "terraform": {
                "required_version": ">= 0.10, < 0.12",
                "backend": {
                    "s3": {
                        "key": "dpk/dpk-{component}/{component}.tfstate".format(component=component),
                        "encrypt": 1
                    }
                }
            }
        }

        provider = {
            "provider": {
                provider: {
                    "profile": "${var.env}",
                    "region": "${var.region}"
                }
            }
        }

        target_configuration.update(terraform)
        target_configuration.update(provider)

    def __create_module_configuration(self, element, catalog_name, provider_specific_catalog, parameter_groups):
        element_type = element["module"]

        if element_type not in provider_specific_catalog:
            raise TerraformPlugin.Error("{element_type} not found in catalog named {catalog_name}".format(
                element_type=element_type,
                catalog_name=catalog_name
            ))

        module_configuration = {
            "source": provider_specific_catalog[element_type]
        }

        parameters = self.build_parameters(element["parameters"], parameter_groups)
        module_configuration.update(parameters)

        name = element["name"]

        return {
            name: module_configuration
        }

