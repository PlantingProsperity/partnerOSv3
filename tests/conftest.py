def pytest_addoption(parser):
    parser.addoption("--stress", action="store_true", default=False, help="run stress tests")
