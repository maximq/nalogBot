import json
import os

from vkwave.bots import EventTypeFilter, SimpleLongPollBot
from vkwave.bots.core.dispatching import filters
from vkwave.bots.fsm import FiniteStateMachine, StateFilter, ForWhat, State, ANY_STATE
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from vkwave.types.bot_events import BotEventType

from doc_list import docs

token = os.environ['VK_TOKEN']
group_id = int(os.environ['GROUP_ID'])
bot = SimpleLongPollBot(token, group_id=group_id)


fsm = FiniteStateMachine()
bot.router.registrar.add_default_filter(StateFilter(fsm, ..., ..., always_false=True))
bot.router.registrar.add_default_filter(
    EventTypeFilter(BotEventType.MESSAGE_NEW.value)
)  # we don't want to write it in all handlers.


class MyState:
    tax = State("tax")
    number = State("number")


#  exiting interview (work with any state because of `state=ANY_STATE`)
@bot.message_handler(
    filters.PayloadFilter({"button": "exit"}), StateFilter(fsm=fsm, state=ANY_STATE, for_what=ForWhat.FOR_USER)
)
async def exit_handler(event: bot.SimpleBotEvent):
    if await fsm.get_data(event, for_what=ForWhat.FOR_USER) is not None:
        await fsm.finish(event=event, for_what=ForWhat.FOR_USER)
    kb = Keyboard()
    kb.add_text_button("Начать", payload={"button": "start"})
    await event.answer("Здравствуйте, я ваш помощник по составлению декларации по форме 3-НДФЛ. Давайте продолжим - нажмите «Начать» 👌🏻", keyboard=kb.get_keyboard())
    return


# starting interview (has default filter that will reject messages if state exists)
@bot.message_handler(filters.PayloadFilter({"button": "start"}))
async def start_handler(event: bot.SimpleBotEvent):
    await fsm.set_state(event=event, state=MyState.tax, for_what=ForWhat.FOR_USER)
    kb = Keyboard(one_time=True)
    kb.add_text_button("Имущественный вычет", payload={"button": "property"})
    kb.add_text_button("Вычет на лечение", payload={"button": "healing"})
    kb.add_row()
    kb.add_text_button("Вычет на обучение", payload={"button": "study"})
    kb.add_text_button("Продажа автомобиля", payload={"button": "car"})
    kb.add_row()
    kb.add_text_button("Продажа недвижимости", payload={"button": "realty"})
    kb.add_text_button("Сдача недвижимости в аренду", payload={"button": "rent"})
    kb.add_row()
    kb.add_text_button("Отмена", color=ButtonColor.NEGATIVE, payload={"button": "exit"})
    await event.answer("Выберите, пожалуйста, вид возврата и ознакомьтесь с необходимым пакетом документов", keyboard=kb.get_keyboard())
    return
    # return ("Выберите, пожалуйста, вид возврата:", keyboard=kb.get_keyboard())


@bot.message_handler(StateFilter(fsm=fsm, state=MyState.tax, for_what=ForWhat.FOR_USER),)
async def name_handler(event: bot.SimpleBotEvent):
    await fsm.set_state(
        event=event,
        state=MyState.number,
        for_what=ForWhat.FOR_USER,
        extra_state_data={"tax": event.object.object.message.text},
    )
    payload = json.loads(event.object.object.message.payload)
    with open(docs.get(payload.get('button')), 'r') as file:
        description_docs = file.read()
    # extra_state_data is totally equal to fsm.add_data(..., state_data={"name": event.object.object.message.text})

    kb = Keyboard(one_time=True)
    kb.add_text_button("Отмена", payload={"button": "exit"})
    await event.answer(description_docs)
    await event.answer('Оставьте номер телефона для связи', keyboard=kb.get_keyboard())
    return


@bot.message_handler(StateFilter(fsm=fsm, state=MyState.number, for_what=ForWhat.FOR_USER),)
async def age_handler(event: bot.SimpleBotEvent):
    if not event.object.object.message.text.isdigit():
        return f"Необходим номер телефона в формате 79XXXXXXXXX"
    await fsm.add_data(
        event=event,
        for_what=ForWhat.FOR_USER,
        state_data={"number": event.object.object.message.text},
    )
    user_data = await fsm.get_data(event=event, for_what=ForWhat.FOR_USER)

    # we finish interview and... we should delete user's state from storage.
    # `fsm.finish` will do it by itself.
    await fsm.finish(event=event, for_what=ForWhat.FOR_USER)
    await event.answer(f"Введенны следующие данные: - {user_data['tax']} - {user_data['number']}")
    return await exit_handler(event)


@bot.message_handler()
async def echo_handler(event: bot.SimpleBotEvent):
    return await exit_handler(event)  # Возврат в начало


bot.run_forever()