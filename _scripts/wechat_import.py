import json
import os
import time
from pprint import pprint
from pathlib import Path

import requests

APP_ID = 'wx36c6dbf8b59bdb4f'
APP_SECRET = 'b753ab2203e83db494818999af7a23fb'
API_CHUNK_SIZE = 15

WECHAT_URL = 'https://api.weixin.qq.com'
API_URL = f'{WECHAT_URL}/tcb'
API_ENV = 'cloud1-4g09gzne0a03d7bd'

BASE_PATH = Path('data/wechat_import/')
IMG_PATH = BASE_PATH / 'img'


def invoke_article_function(access_token, function_name, data):
    data['func'] = function_name
    return invoke_cloud_function(access_token, 'articles', data)


def invoke_cloud_function(access_token, function_name, data):
    return requests.post(f'{API_URL}/invokecloudfunction?',
                         data=json.dumps(data),
                         params=dict(
                             access_token=access_token,
                             env=API_ENV,
                             name=function_name,
                         )).json()


def get_upload_link(access_token, path):
    return requests.post(f'{API_URL}/uploadfile?',
                         data=json.dumps(dict(
                             env=API_ENV,
                             path=path,
                         )),
                         params=dict(
                             access_token=access_token,
                         )).json()


def get_access_token():
    access_token_file = BASE_PATH / '_access_token'
    
    if access_token_file.exists():
        with access_token_file.open('r') as f:
            access_token, expires = f.read().splitlines()
            expires = int(expires)
            now = int(time.time())
            if now < expires:
                print(f'Returning cached access token "{access_token}"')
                return access_token
    
    res = requests.get(
        f'{WECHAT_URL}/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&'
        f'secret={APP_SECRET}')
    res = res.json()
    if 'errcode' in res and res['errcode'] != 0:
        print(f'Failed to get access token: {res["errmsg"]}')
        return
    
    access_token = res['access_token']
    expires = int(time.time() + res['expires_in'] * 0.9)
    with access_token_file.open('w') as f:
        f.write(f'{access_token}\n{expires}')
    
    print(f'Got access token "{access_token}"')
    return access_token


def run():
    import_data_file = BASE_PATH / 'data.json'
    if not import_data_file.exists():
        print('No data to import')
        return
    with import_data_file.open('r') as f:
        import_data = json.load(f)
    
    if not import_data:
        print('No data to import')
        return
    
    # Do it in chunks just to make sure the API doesn't timeout
    output_data = []
    output_chunks = [output_data]
    images_upload = []
    updated_articles = dict()
    for article_id, article_data in import_data.items():
        has_data = False
        if isinstance(article_data, dict):
            if output_data is None:
                output_data = []
                output_chunks.append(output_data)
            
            article_data['_id'] = article_id
            output_data.append(article_data)
            has_data = True
            
            if len(output_data) == API_CHUNK_SIZE:
                output_data = None
        
        img_path = IMG_PATH / f'{article_id}.jpg'
        if img_path.exists():
            images_upload.append((article_id, img_path))
        elif not has_data:
            updated_articles[article_id] = True
    
    access_token = get_access_token()
    
    failed_article_count = 0
    # TODO: Check access token expiry after each action and update if necessary
    for output_chunk in output_chunks:
        if not output_chunk:
            continue
        
        print(f'Importing {len(output_chunk)} article(s)...')
        result = invoke_article_function(access_token, 'importArticles',
                                         dict(articles=output_chunk))
        if 'errcode' in result and result['errcode'] != 0:
            print(f'  Error: {result["errcode"]} "{result["errmsg"]}"')
            continue
        
        results = json.loads(result['resp_data'])
        if 'errors' in results:
            for err in results['errors']:
                print(f'  {err["errCode"]}: "{err["errMsg"]}"')
        
        successful_articles = results['docs']
        for article_id in successful_articles:
            updated_articles[article_id] = True
        failed_article_count += len(output_chunk) - len(successful_articles)
        pass

    failed_image_count = 0
    print(f'Uploading {len(images_upload)} image(s)')
    for article_id, img_path in images_upload:
        print(f'  "{img_path.name}"')
        cloud_path = f'img/article/{img_path.name}'
        results = get_upload_link(access_token, cloud_path)
        if 'errcode' in results and results['errcode'] != 0:
            print(f'  {results["errcode"]}: "{results["results"]}"')
            if article_id in updated_articles:
                updated_articles[article_id] = False
            failed_image_count += 1
            continue

        try:
            do_upload(results, cloud_path, img_path)
            if article_id not in updated_articles:
                updated_articles[article_id] = True
            img_path.unlink()
        except:
            if article_id in updated_articles:
                updated_articles[article_id] = False

            failed_image_count += 1
        pass
    
    if updated_articles:
        for article_id, val in updated_articles.items():
            if val:
                del import_data[article_id]
            else:
                import_data[article_id] = True
            pass
        
        with import_data_file.open('w') as f:
            json.dump(import_data, f)

    if failed_article_count > 0:
        print(f'! {failed_article_count} article(s) failed to update')
    if failed_image_count > 0:
        print(f'! {failed_image_count} image(s) failed to upload')


def do_upload(results, cloud_path, file_path):
    return requests.post(results['url'],
                         files={
                             'key': cloud_path,
                             'Signature': results['authorization'],
                             'x-cos-security-token': results['token'],
                             'x-cos-meta-fileid': results['cos_file_id'],
                             'file': file_path.open('rb'),
                         })


if __name__ == '__main__':
    run()

    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
