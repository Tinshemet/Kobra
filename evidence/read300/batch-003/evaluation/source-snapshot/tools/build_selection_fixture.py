"""Author-fixed pilot references. Run before inference, never derive gold from predictions."""
import json
from pathlib import Path

SLOTS = ('predicate','agent','patient','recipient','negation','condition','time','quantity','attribution','modality')
def f(act,predicate,**kw):
    result={'act':[act], **{s:['NONE'] for s in SLOTS}}
    result['predicate']=[predicate]
    result.update({k:v if isinstance(v,list) else [v] for k,v in kw.items()})
    return result
rows=[]
def add(group,text,*frames):
    rows.append({'id':f'C{len(rows)+1:03d}','group':group,'text':text,'expected':list(frames)})
add('simple','Open the window.',f('request','Open',patient=['the window','window']))
add('simple','Delete the draft.',f('request','Delete',patient=['the draft','draft']))
add('simple','Send Maya the invoice.',f('request','Send',patient=['the invoice','invoice'],recipient='Maya'))
add('simple','Lena repaired the bicycle.',f('assertion','repaired',agent='Lena',patient=['the bicycle','bicycle']))
add('simple','The alarm rang.',f('assertion','rang',agent=['The alarm','alarm']))
add('question','Did Maya send the invoice?',f('question','send',agent='Maya',patient=['the invoice','invoice']))
add('question','Did you lock the cabinet?',f('question','lock',agent='you',patient=['the cabinet','cabinet']))
add('question','Is the server running?',f('question','running',agent=['the server','server']))
add('question','Who deleted the file?',f('question','deleted',agent='Who',patient=['the file','file']))
add('question','Has Lena checked the schedule?',f('question','checked',agent='Lena',patient=['the schedule','schedule']))
add('negation','Do not erase the logs.',f('request','erase',patient=['the logs','logs'],negation='not'))
add('negation','Never share the password.',f('request','share',patient=['the password','password'],negation='Never'))
add('negation','Maya did not sign the contract.',f('assertion','sign',agent='Maya',patient=['the contract','contract'],negation='not'))
add('negation',"Don't move the chair.",f('request','move',patient=['the chair','chair'],negation="Don't"))
add('negation','The lamp is not working.',f('assertion','working',agent=['The lamp','lamp'],negation='not'))
add('condition','Send the invoice if Maya approves.',f('request','Send',patient=['the invoice','invoice'],condition='if Maya approves'))
add('condition','Do not unlock the door unless I agree.',f('request','unlock',patient=['the door','door'],negation='not',condition='unless I agree'))
add('condition','If it rains, close the windows.',f('request','close',patient=['the windows','windows'],condition='If it rains'))
add('condition','Publish the article only if Lena agrees.',f('request','Publish',patient=['the article','article'],condition='only if Lena agrees'))
add('condition','Restart the service unless the backup fails.',f('request','Restart',patient=['the service','service'],condition='unless the backup fails'))
add('time','Send the package tomorrow.',f('request','Send',patient=['the package','package'],time='tomorrow'))
add('time','Finish the report before noon.',f('request','Finish',patient=['the report','report'],time='before noon'))
add('time','After the meeting, call Maya.',f('request','call',patient='Maya',time='After the meeting'))
add('time','Lena submitted the form yesterday.',f('assertion','submitted',agent='Lena',patient=['the form','form'],time='yesterday'))
add('time','Back up the files every Friday.',f('request','Back up',patient=['the files','files'],time='every Friday'))
add('quantity','Print three copies.',f('request','Print',patient=['three copies','copies'],quantity='three'))
add('quantity','Order exactly two batteries.',f('request','Order',patient=['exactly two batteries','two batteries','batteries'],quantity='exactly two'))
add('quantity','Maya bought five notebooks.',f('assertion','bought',agent='Maya',patient=['five notebooks','notebooks'],quantity='five'))
add('quantity','Keep at least four backups.',f('request','Keep',patient=['at least four backups','four backups','backups'],quantity='at least four'))
add('quantity','Do not send more than ten messages.',f('request','send',patient=['more than ten messages','ten messages','messages'],quantity='more than ten',negation='not'))
add('attribution','Maya says the backup failed.',f('assertion','failed',agent=['the backup','backup'],attribution=['Maya','Maya says']))
add('attribution','According to Lena, the server crashed.',f('assertion','crashed',agent=['the server','server'],attribution=['According to Lena','Lena']))
add('attribution','Omar reports that the parcel arrived.',f('assertion','arrived',agent=['the parcel','parcel'],attribution=['Omar','Omar reports']))
add('attribution','Maya believes the alarm is broken.',f('assertion','broken',agent=['the alarm','alarm'],attribution=['Maya','Maya believes']))
add('attribution','According to Omar, Lena did not sign the form.',f('assertion','sign',agent='Lena',patient=['the form','form'],negation='not',attribution=['According to Omar','Omar']))
add('modality','You may open the window.',f('assertion','open',agent='You',patient=['the window','window'],modality='may'))
add('modality','Maya must submit the form.',f('assertion','submit',agent='Maya',patient=['the form','form'],modality='must'))
add('modality','The server might fail.',f('assertion','fail',agent=['The server','server'],modality='might'))
add('modality','Lena can repair the bicycle.',f('assertion','repair',agent='Lena',patient=['the bicycle','bicycle'],modality='can'))
add('modality','You must not disclose the code.',f('assertion','disclose',agent='You',patient=['the code','code'],negation='not',modality='must'))
add('coordination','Copy the file and rename the folder.',f('request','Copy',patient=['the file','file']),f('request','rename',patient=['the folder','folder']))
add('coordination','Maya opened the door and closed the window.',f('assertion','opened',agent='Maya',patient=['the door','door']),f('assertion','closed',agent='Maya',patient=['the window','window']))
add('coordination','Save the document, then close the editor.',f('request','Save',patient=['the document','document']),f('request','close',patient=['the editor','editor'],time='then'))
add('coordination','Do not print the memo or send the email.',f('request','print',patient=['the memo','memo'],negation='not'),f('request','send',patient=['the email','email'],negation='not'))
add('coordination','If Maya agrees, archive the folder and delete the draft.',f('request','archive',patient=['the folder','folder'],condition='If Maya agrees'),f('request','delete',patient=['the draft','draft'],condition='If Maya agrees'))
add('voice_reference','The report was approved by Maya.',f('assertion','approved',agent='Maya',patient=['The report','report']))
add('voice_reference','The parcel was not delivered by Omar.',f('assertion','delivered',agent='Omar',patient=['The parcel','parcel'],negation='not'))
add('voice_reference','She repaired it.',f('assertion','repaired',agent='She',patient='it'))
add('voice_reference','Send him the receipt.',f('request','Send',patient=['the receipt','receipt'],recipient='him'))
add('voice_reference','Those files were deleted yesterday.',f('assertion','deleted',patient=['Those files','files'],time='yesterday'))
assert len(rows)==50
payload={'version':'selection-pilot-gold-1','annotation':'Agent-authored before inference; not independently reviewed; bounded slot contract, not all meaning.',
         'contract':'One main frame per action; attributed/conditional content is preserved in slots. Articles may be included or omitted in listed noun variants. Explicitly modal declaratives are assertions. Pronouns remain source-bound, unresolved. Phrasal verbs are whole predicates.',
         'cases':rows}
path=Path('tests/fixtures/selection-50.json')
with path.open('x') as stream:json.dump(payload,stream,indent=2);stream.write('\n')
