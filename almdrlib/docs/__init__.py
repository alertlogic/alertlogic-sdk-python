import os

from almdrlib.session import Session
from almdrlib.docs.service import ServiceDocGenerator


def make_documentation(dir, session=None):
    """Creates documentation for Alert Logic SDK

    Enumerates all services and generates rst files for sphinx documentation

    :param dir: The directory to write the files to. Each
        service's documentation is loacated at
        dir/services/[service name].rst file

    :param session: The IWS Services session
    """

    doc_path = os.path.join(dir, 'site', 'services')
    if not os.path.exists(doc_path):
        os.makedirs(doc_path)

    for name in Session.list_services():
        doc = ServiceDocGenerator(
                service_name=name,
                spec=Session.get_service_api(name)
            ).get_documentation()

        service_doc_path = os.path.join(
            doc_path, name + '.rst')
        with open(service_doc_path, 'w+') as f:
            f.writelines(f"{line}\n" for line in doc)
