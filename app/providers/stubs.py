class DBSessionStub:
    """Заглушка получения сессии БД."""

    def __init__(self):
        raise NotImplementedError


class CeleryStub:
    """Заглушка получения приложения Celery."""

    def __init__(self):
        raise NotImplementedError


class VCDServiceStub:
    """Заглушка получения сервиса vCD."""

    def __init__(self):
        raise NotImplementedError


class VCDControllerStub:
    """Заглушка получения контроллера vCD."""

    def __init__(self):
        raise NotImplementedError


class VMRepositoryStub:
    """Заглушка получения ВМ репозитория."""

    def __init__(self):
        raise NotImplementedError


class SettingsRepositoryStub:
    """Заглушка получения репозитория настроек."""

    def __init__(self):
        raise NotImplementedError


class TemplateCatalogRepositoryStub:
    """Заглушка получения репозитория каталога шаблонов."""

    def __init__(self):
        raise NotImplementedError


class Jinja2TemplatesStub:
    """Заглушка получения шаблонов Jinja2."""

    def __init__(self):
        raise NotImplementedError
