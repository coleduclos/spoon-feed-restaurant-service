import boto3
import json
import decimal

print('Loading function')

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
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
    
def lambda_handler(event, context):
    print ('Lambda Event Handler: duclos-app-restaurant-service')
    operations = {
        'GET': lambda dynamo, table_attr, x: dynamo.query(
                KeyConditionExpression='#partitionkey = :partitionkeyval',
                ExpressionAttributeNames={
                    '#partitionkey' : table_attr['table_pkey']
                },
                ExpressionAttributeValues={
                    ':partitionkeyval' : x[table_attr['table_pkey']]
                }
            )
    }

    dynamo_tables = {
        'recommendations' :
        {
            'table_name' : 'duclos-app-recommendations',
            'table_pkey' : 'user-id'
        }
    }
    operation = event['httpMethod']

    if operation in operations:
        if operation == 'GET':
            payload = event['pathParameters']
            dynamo_table = payload['dynamo-table']
            if dynamo_table in dynamo_tables:
                dynamo = boto3.resource('dynamodb').Table(dynamo_tables[dynamo_table]['table_name'])
                response = operations[operation](dynamo, dynamo_tables[dynamo_table], payload)
            else:
                return respond(ValueError('Unsupported query "{}"'.format(dynamo_table)))

        if 'Items' in response:
            response = response['Items']
        else:
            response = None

        return respond(None, response)

    else:
        return respond(ValueError('Unsupported method "{}"'.format(operation)))