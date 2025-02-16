import concurrent.futures
import asyncio
import concurrent.futures
import copy
import os.path

import httpx
import jsonlines

base_url = r'https://artofproblemsolving.com/m/community/ajax.php'

headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://artofproblemsolving.com",
    "Referer": "https://artofproblemsolving.com/",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="198"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}


# 创建全局的异步HTTP客户端对象
async def create_client():
    client = httpx.AsyncClient(timeout=30.0, )
    return client


# 异步函数，用于获取API数据
async def get_api_data(data, client):
    for i in range(10):
        try:
            res = await client.post(url=base_url, data=data, headers=headers)
            if res.status_code == 200:
                await asyncio.sleep(0.6)
                return res.json()
        except Exception as e:
            await asyncio.sleep(5)
    raise Exception('未获取到数据')


async def get_class_page_data(category_id, client, semaphore, category_name_list=None):
    if not category_name_list:
        category_name_list = []
    else:
        category_name_list = copy.deepcopy(category_name_list)

    data = {
        "category_id": category_id,
        "a": "fetch_category_data",
        "aops_logged_in": True,
        "aops_user_id": 1,
        "aops_session_id": "21d6f40cfb511982e4424e0e250a9557"
    }

    for _ in range(5):
        try:
            res = await get_api_data(data, client)
            category_name = res['response']['category']['category_name']
            category_name = category_name.replace('\\', '').replace('/', '')
            category_name_list.append(category_name)
            page_data_list = []
            tasks = []
            for item in res['response']['category']['items']:
                # print(item)
                if item['item_type'] in ["folder", "view_posts"]:
                    page_data_list.append({
                        "item_id": item['item_id'], "item_text": item['item_text'],
                        "item_type": item['item_type'], "item_subtitle": item['item_subtitle'],
                    })
                else:
                    if item["post_data"]['topic_id'] != 0:
                        task = asyncio.create_task(get_view_item(item, client))
                        tasks.append(task)

            start_num = 50
            while True:
                new_data = {
                    "sought_category_ids": "[]",
                    "parent_category_id": category_id,
                    "seek_items": 1,
                    "start_num": start_num,
                    "log_visit": 0,
                    "a": "fetch_items_categories",
                    "aops_logged_in": True,
                    "aops_user_id": 1,
                    "aops_session_id": "21d6f40cfb511982e4424e0e250a9557"
                }

                res = await get_api_data(new_data, client)
                if res['response'].get('no_more_items', False):
                    break
                for item in res['response']['new_items']:
                    if item['item_type'] in ["folder", "view_posts"]:
                        page_data_list.append({
                            "item_id": item['item_id'], "item_text": item['item_text'],
                            "item_type": item['item_type'], "item_subtitle": item['item_subtitle'],
                        })
                    else:
                        if item["post_data"]['topic_id'] != 0:
                            task = asyncio.create_task(get_view_item(item, client))
                            tasks.append(task)

                start_num += 10

            for item in page_data_list:
                if item['item_type'] == "folder" or item['item_type'] == "view_posts":

                    await get_class_page_data(item['item_id'], client, semaphore, category_name_list)

            res = await asyncio.gather(*tasks)
            if not res:
                return None
            file_name = category_name_list[-1]
            dir_output = r'D:\Code\python_toolkit\data'
            file_path = os.path.join(dir_output, *category_name_list[:-1])

            if not os.path.exists(file_path):
                os.makedirs(file_path)
            with jsonlines.open(f'{file_path}/{file_name}.jsonl', 'w') as f:
                f.write_all(res)

            down_base_url = rf'https://artofproblemsolving.com/downloads/printable_post_collections/{category_id}'
            import requests
            response = requests.get(down_base_url)
            with open(os.path.join(file_path, f'{file_name}.pdf'), 'wb') as f:
                f.write(response.content)

            print(category_name_list, '处理完成')
            break
        except Exception as e:
            print(e)
            raise

    return


async def get_view_item(item, client):
    data = {
        "topic_id": item["post_data"]['topic_id'],
        "a": "fetch_topic",
        "aops_logged_in": True,
        "aops_user_id": 1,
        "aops_session_id": "21d6f40cfb511982e4424e0e250a9557"
    }
    new_item = copy.deepcopy(item)
    # async  with semaphore:
    res = await get_api_data(data, client)
    if res:
        new_item['topic_title'] = res['response']['topic']['topic_title']
        new_item['topic_type'] = res['response']['topic']['topic_type']
        new_item['source'] = res['response']['topic']['source']
        new_item['tags'] = [i['tag_text'] for i in res['response']['topic']['tags']]
        new_item['posts_data'] = [i['post_canonical'] for i in res['response']['topic']['posts_data']]

    return new_item


async def async_main(task_id):
    client = await create_client()
    semaphore = asyncio.Semaphore(100)
    await get_class_page_data(task_id, client, semaphore, [])
    # await  asyncio.sleep(2)


def main(task_id):
    asyncio.run(async_main(task_id))


if __name__ == '__main__':
    # temp_list1 = [14, 16, 15, 58, 59, 62, 3752401, 3296298, 2958087, 3754998, 116, 40244]
    temp_list1 = [14,  15, 58, 59, 62, 3752401, 3296298, 2958087, 3754998, 116]
    # temp_list1 = [3158, 3213, 3159, 305479, 3160, 3161, 72755, 566954, 186277, 3162, 2650964, 3163, 3164, 3165, 3166,
    #               2482163, 3167, 2418240, 3208, 3168, 3979311, 854082, 3169, 3236075, 2474643, 2513798, 186102, 3170,
    #               3171, 3212, 3172, 3173, 1254487, 3174, 3175, 3176, 3177, 3178, 3179, 182662, 3180, 3181, 3182, 3198,
    #               3214, 3215, 305478, 3183, 3245, 3217, 3184, 3185, 3186, 3216, 4044796, 3373152, 645389, 3187, 2476037,
    #               953270, 3209, 3188, 400373, 3189, 3210, 3190, 3191, 3192, 3193, 3194, 3195, 3221, 3211, 3196, 3197,
    #               3199, 3200, 3150212, 587379, 3201, 680930, 3202, 3220, 879687, 3219, 3203, 3218, 3205, 3206, 3207,
    #               2476722]

    with concurrent.futures.ProcessPoolExecutor() as slaved_pool:
        slaved_pool.map(main, temp_list1)
        # slaved_pool.map(main, [14])
