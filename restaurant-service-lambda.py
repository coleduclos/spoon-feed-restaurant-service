import boto3
import json
import decimal

print('Loading function')

dynamo_tables = {
    'recommendations' :
    {
        'table_name' : 'duclos-app-recommendations',
        'table_pkey' : 'user-id',
        'table_skey' : 'geohash',
        'operations' : { 'GET' : lambda pkey, query_params: get_recommendation_details(pkey, query_params) } 
    },
    'restaurants' :
    {
        'table_name' : 'duclos-app-restaurants',
        'index_name' : 'restaurant-id-index',
        'table_pkey' : 'restaurant-id',
        'operations' : { 'GET' : lambda pkey, query_params=None: get_restaurant_details(pkey, query_params) } 
    }
}

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def respond(err, response=None):
    print response
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(response, cls=DecimalEncoder),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
    }

def get_recommendation_details(pkey, query_params):
    table_attr = dynamo_tables['recommendations']
    dynamo = boto3.resource('dynamodb').Table(table_attr['table_name'])
    skey_lower = query_params['skey_lower']
    skey_upper = query_params['skey_upper']
    print('Querying recommendation details for {} between {} and {}'.format(pkey, skey_lower, skey_upper))
    recommendations = dynamo.query(
                KeyConditionExpression='#partitionkey = :partitionkeyval AND #sortkey BETWEEN :sortkeylower AND :sortkeyupper',
                ExpressionAttributeNames={
                    '#partitionkey' : table_attr['table_pkey'],
                    '#sortkey' : table_attr['table_skey']
                },
                ExpressionAttributeValues={
                    ':partitionkeyval' : pkey,
                    ':sortkeylower' : skey_lower,
                    ':sortkeyupper' : skey_upper
                }
            )
    response = []
    if 'Items' in recommendations and len(recommendations['Items']) > 0 and 'recommendation-map' in recommendations['Items'][0]:
            recommendation_map = recommendations['Items'][0]['recommendation-map']
            for r in recommendation_map:
                details = get_restaurant_details(r)
                if details is not None:
                    details['spoon-feed-value'] = recommendation_map[r]
                    response.append(details)
    return response

def get_restaurant_details(pkey, query_params=None):
    table_attr = dynamo_tables['restaurants']
    dynamo = boto3.resource('dynamodb').Table(table_attr['table_name'])
    print('Querying restaurant details for {}'.format(pkey))
    restaurant = dynamo.query(
                    IndexName=table_attr['index_name'],
                    KeyConditionExpression='#partitionkey = :partitionkeyval',
                    ExpressionAttributeNames={
                        '#partitionkey' : table_attr['table_pkey']
                    },
                    ExpressionAttributeValues={
                        ':partitionkeyval' : pkey
                    }
                )
    if 'Items' in restaurant:
        details = restaurant['Items']
        if len(details) > 0:
            response = details[0]
            return response

def lambda_handler(event, context):
    print ('Lambda Event Handler: restaurant-service')
    operation = event['httpMethod']
    path_params = event['pathParameters']
    dynamo_table = path_params['dynamo-table']
    pkey = path_params['pkey']
    query_params = event['queryStringParameters']

    if dynamo_table in dynamo_tables:
        if operation in dynamo_tables[dynamo_table]['operations']:
            response = dynamo_tables[dynamo_table]['operations'][operation](pkey, query_params)
        else:
            return respond(ValueError('Unsupported method "{}" - {}'.format(dynamo_table, operation)))
    else:
        return respond(ValueError('Unsupported query "{}"'.format(dynamo_table)))        

    return respond(None, response)