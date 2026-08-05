from router import ModelRouter

print('Sarembok Runtime Online')

router = ModelRouter()

while True:

    command = input('Sarembok> ')

    if command.lower() == 'exit':
        break

    response = router.process(command)

    print(response)
