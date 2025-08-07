class DummyLimiter:
    def limit(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

limiter = DummyLimiter()
