from flask import request


def get_page_params(default_size: int = 10, max_size: int = 100) -> tuple[int, int]:
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", default_size)), 1), max_size)
    return page, page_size


def pagination_payload(pagination) -> dict:
    return {
        "items": [item.to_dict() for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
        "pages": pagination.pages,
    }

