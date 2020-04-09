import keyboardKeys
import PySimpleGUI as sg

# shows listbox popup

class ListBoxChoice :
    def __init__(self,choice,index) :
        self.choice=choice
        self.index=index

    def __str__(self) :
        return str(self.choice)

    def getIndex(self) :
        return self.index

def showListBoxPopup(choices,text) :
    listBoxChoices=[]
    index=0
    maxWidth=0
    for choice in choices :
        listBoxChoices.append(ListBoxChoice(choice,index))
        index+=1
        if len(str(choice)) > maxWidth :
            maxWidth=len(str(choice))
        

    layout = [[sg.Text(text)],
              [sg.Listbox(listBoxChoices,
                          key='_choices_listbox_',
                          select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                          default_values=[listBoxChoices[0]],
                          size=(maxWidth+2,len(listBoxChoices)),
                          no_scrollbar = True)],
              [sg.RButton('OK',key='_ok_button_')]]
    window = sg.Window(text,layout,return_keyboard_events=True,keep_on_top=True,disable_minimize=True)
    while True :
        button,value = window.Read()
        if (button == '_ok_button_') or (button == None) or (button == keyboardKeys.Enter):
            window.close()
            try :
                return str(value['_choices_listbox_'][0])
            except:
                print('No choice value=',value['_choices_listbox_'])
                return choices[0]

        if button == keyboardKeys.Down :
            index=value['_choices_listbox_'][0].getIndex()
            if index < len(listBoxChoices)-1 :
                index+=1
            window.FindElement('_choices_listbox_').SetValue([listBoxChoices[index]])

        if button == keyboardKeys.Up :
            index=value['_choices_listbox_'][0].getIndex()
            if index > 0 :
                index-=1
            window.FindElement('_choices_listbox_').SetValue([listBoxChoices[index]])
          

#test = ['a','b','LLLLLLARGE']
#print(showListBoxPopup(test,'TEST'))
