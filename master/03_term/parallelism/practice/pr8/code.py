def homework_basic(data_sequence):
    ''' 
    Базовое задание: 
    устраните зависимости в этом алгоритме обработки временных рядов
    '''
    result = []

    current = data_sequence[0]

    for i in range(1, len(data_sequence)):
        # Тут найти и устранить все зависимости
        current = current * 0.9 + data_squence[i] * 0.1