from inspect import Parameter, signature

from fastapi import Form


def as_form(cls):
    new_params = []

    # 모델 전체 example 읽기
    model_json_schema_extra = getattr(cls, "model_config", {}).get("json_schema_extra", {}) or {}
    model_examples = model_json_schema_extra.get("examples", [])

    first_example = model_examples[0] if model_examples else {}

    for field_name, model_field in cls.model_fields.items():
        field_info = model_field
        field_json_schema_extra = getattr(field_info, "json_schema_extra", None) or {}

        form_kwargs = {}

        if field_info.description:
            form_kwargs["description"] = field_info.description

        # 1순위: 필드 자체 examples / example
        if getattr(field_info, "examples", None):
            form_kwargs["examples"] = field_info.examples

        elif "openapi_examples" in field_json_schema_extra:
            form_kwargs["openapi_examples"] = field_json_schema_extra["openapi_examples"]

        elif "examples" in field_json_schema_extra:
            form_kwargs["examples"] = field_json_schema_extra["examples"]

        elif "example" in field_json_schema_extra:
            form_kwargs["example"] = field_json_schema_extra["example"]

        # 2순위: 모델 전체 example에서 현재 필드 값 꺼내기
        elif field_name in first_example:
            value = first_example[field_name]

            # Swagger UI는 openapi_examples 지원이 더 나음
            form_kwargs["openapi_examples"] = {
                "default": {
                    "summary": f"{field_name} example",
                    "value": value,
                }
            }

            # 필요하면 같이 넣어도 됨
            form_kwargs["example"] = value

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

    _as_form.__signature__ = signature(_as_form).replace(parameters=new_params)
    return _as_form