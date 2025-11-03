import logging, os

def setup_logging(output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "vttfg.log")
    # add only one file handler and one stream handler
    root = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(fh)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(ch)
    root.setLevel(logging.INFO)
    return log_path, True
