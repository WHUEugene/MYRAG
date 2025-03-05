from document_server import celery

if __name__ == '__main__':
    celery.worker_main(['worker', '--loglevel=info'])
