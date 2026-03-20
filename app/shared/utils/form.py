from inspect import Parameter, signature

from fastapi import Form


def as_form(cls):
    new_params = []

    for field_name, model_field in cls.model_fields.items():
        field_info = model_field
        json_schema_extra = field_info.json_schema_extra or {}

        form_kwargs = {}

        if field_info.description:
            form_kwargs["description"] = field_info.description

        # examples 우선
        if field_info.examples:
            form_kwargs["examples"] = field_info.examples
        elif "examples" in json_schema_extra:
            form_kwargs["examples"] = json_schema_extra["examples"]
        elif "example" in json_schema_extra:
            form_kwargs["example"] = json_schema_extra["example"]

        default = (
            Form(..., **form_kwargs)
            if model_field.is_required()
            else Form(model_field.default, **form_kwargs)
        )

        new_params.append(
            Parameter(
                field_name,
                Parameter.POSITIONAL_ONLY,
                default=default,
                annotation=model_field.annotation,
            )
        )

    async def _as_form(**data):
        return cls(**data)

    sig = signature(_as_form).replace(parameters=new_params)
    _as_form.__signature__ = sig
    return _as_form