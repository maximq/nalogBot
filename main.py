import json

from vkwave.bots import EventTypeFilter, SimpleLongPollBot
from vkwave.bots.core.dispatching import filters
from vkwave.bots.fsm import FiniteStateMachine, StateFilter, ForWhat, State, ANY_STATE
from vkwave.bots.utils.keyboards.keyboard import Keyboard, ButtonColor
from vkwave.types.bot_events import BotEventType

from doc_list import docs

token = '91da994816a4284e70457c25158f5f3e935e5e657631f310f75c4d5d9e39cdffd007f738cbadb53662cd4'
group_id = 142414008
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
@bot.message_handler(bot.text_filter("начать"))
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
    await event.answer(description_docs)
    return 'Оставьте номер телефона для связи'


@bot.message_handler(StateFilter(fsm=fsm, state=MyState.number, for_what=ForWhat.FOR_USER),)
async def age_handler(event: bot.SimpleBotEvent):
    if not event.object.object.message.text.isdigit():
        return f"Необходимы цифры!"
    await fsm.add_data(
        event=event,
        for_what=ForWhat.FOR_USER,
        state_data={"number": event.object.object.message.text},
    )
    user_data = await fsm.get_data(event=event, for_what=ForWhat.FOR_USER)

    # we finish interview and... we should delete user's state from storage.
    # `fsm.finish` will do it by itself.
    await fsm.finish(event=event, for_what=ForWhat.FOR_USER)
    await event.answer(f"Your data - {user_data['tax']} - {user_data['number']}")
    return await exit_handler(event)


@bot.message_handler()
async def echo_handler(event: bot.SimpleBotEvent):
    return await exit_handler(event)  # ...и отвечать на них текстом нового сообщения


bot.run_forever()