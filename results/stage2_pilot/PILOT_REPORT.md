# Stage 2 pilot report

# PILOT -- pipeline validation on dev subjects; no research conclusions.

**PILOT -- pipeline validation on dev subjects; no research conclusions.** Every number below is a pipeline-validation number on six development subjects. Stage 1 and this pilot are for development and tuning only; nothing here answers a pre-registered bar, nothing here is confirmatory, and no result in it should be quoted as a finding about twins.

Generated 2026-07-26T18:34:36Z. Contract: SPEC.md v1.7 (D1-D10). Model leonardo-gemma4-31b-it, temperature 0.0, tp 4, max-model-len 8192. 639 model calls, 0 API calls, $0.00.

## 1. Dev subjects, how they were drawn, and the C00292 story

| canonical_id | name | wiki_status | shuffle_pos | burned_for_qa | Q-A items | imposter donor |
|---|---|---|---|---|---|---|
| C00792 | Frederic Hof | long-tail | 0 |  | 5 | Joshua Landis |
| C00292 | Bassir Pour | long-tail | 1 | **yes** | — (excluded) | — (unused) |
| C02013 | Robert Sampson | has-page | 2 |  | 4 | Doris Meissner |
| C02124 | Samer Shehata | long-tail | 3 |  | 4 | Steven Cook |
| C01677 | Matthew Kroenig | has-page | 5 |  | 1 | Martin Indyk |
| C02006 | Robert Harris | has-page | 6 |  | 3 | Walter Mosley |

**Draw provenance.** Seed 47, drawn 2026-07-26, 578 eligible pool rows. Rule as frozen in D1:

> Eligible = qualifies AND clean AND NOT ambiguous_identity in results/stage2_candidate_pool_v2.csv. Eligible canonical_ids are sorted lexicographically, then shuffled once with random.Random(47).shuffle. Walking that shuffled order, the first 3 ids whose wiki_status is not 'long-tail' and the first 2 whose wiki_status is 'long-tail' are the dev subjects. A subject found broken later stays burned (it is a dev subject forever and is never reused); its replacement is the next id of the same stratum in the same shuffled order. A subject broken for one purpose only is instead retained in place, annotated burned_for_qa, and the next id of its stratum is ADDED alongside it, which is why the subject count can exceed 5. shuffle_pos is the 0-based position of each pick in that shuffled order.

**Burn / replacement event.** `C00292`, mode `retained_in_place`, stratum long-tail, replaced by / joined by `C02124`.

> Yields no Q-A items: DIPLOMATIC LICENSE is a roundtable, and every host turn before one of its guest turns is a statement, so D4's cue filter rejects all of them. Owner decision 2026-07-26: the cue filter stays, the subject stays for classifier sampling and renderer exercise, and a sixth subject is added.

The full burn story — why it produced no Q-A items, what D3.1-r2 and D3.2 recovered, and why the burn does not flip now that it yields one item — is finding 8.9. Operationally: **C00292 is excluded from all 10 prediction prompt sets** by filtering on the `burned_for_qa` annotation (asserted at build, export and verify) and **is included in the classifier prompts**, where it contributes more cases than any other subject.

## 2. Three Q-A items, verbatim, with their full option sets

Straight from T2's committed artifacts. The correct option is marked; the model never sees the marking, and D6 shuffled the positions with a seed derived from the item id.

### `C02124:NPR-12184:2`  (69 words, relaxation rung 0)

**QUESTION**

> Why is a field marshal, according to various surveys, so popular in Egypt?

**A.** distractor

> With any luck, they face - you know, they have to face the - they have to face the voters. Once these things are known, I believe there is a difference between people who are elected with knowledge of this and people who are elected without knowledge of this, like Franken. And the Kihuen situation goes to what we were just talking about.

**B.** distractor

> I think it is. I think the fact that it was such a sort of randomized event and so many - so many lives could have been lost, it really changes the context. I mean, if you think about Unabomber, who killed the same number of people and injured, I believe, fewer than 25 - and his venue was changed. So the fact that this one is not is very interesting to me professionally.

**C.** distractor

> It shouldn't be. But for bishops to defend LGBT people or put themselves out on the line for LGBT people is rather rare. And so one of the things that I try to do in the book is point to bishops and cardinals, in some cases, who are out there and who are supporting their LGBT brothers and sisters and siblings.

**D.** **TRUE ANSWER**

> He's popular for a number of reasons. One, there were many people, of course, who were opposed to the Muslim Brotherhood and Mr. Morsi before he became president. And of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.

**Entity-stripped variant of the true option (the A4.2 re-score):**

> He's popular for a number of reasons. One, there were many people, of course, who were opposed to the [NAME] and [NAME] before he became president. [NAME] of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.

### `C02013:NPR-9480:49`  (228 words, relaxation rung 0)

**QUESTION**

> Let me ask you about that, Robert, because I wonder if this is a chicken and the egg thing, maybe you can't even answer it, but what comes first? Is it the poverty and the unemployment, or is it the gun violence? Because gun violence, when gun violence goes up, that results in people leaving a community, businesses leaving a community. So which of these things happens first?

**A.** distractor

> Well, yes, I will. I'm going to take you to my beef and eggplant fatteh, which actually uses much the same technique. It's like a refined Middle Eastern form of nachos. So you have some pita bread. I use scissors to cut that into triangles and put them in the oven to toast, remove them. And I make a sauce. This time, I add to the Greek yogurt some tahini, lots of lemon juice, bit - you know, two gloves of garlic. And I warm that so it gets slightly aerated and the chill leaves it. And then I make a meat sauce when I've chopped up the eggplant to very small cubes. And I cook those, you know, with onion, add some ground beef and ground cumin, ground coriander. And it's so wonderful for everyone sitting around a table and snatching bits and picking in bits. It's quite messy, but I love that. And, you know, it is in a way for a lot of people, a very unfamiliar way of eating. It's - in itself, we all know what ground meat is, and the pita chips we know, but together, it's different. It's a different thing to eat.

**B.** **TRUE ANSWER**

> That's an excellent question. That's one of the things that we've looked at in research. It's really hard to disentangle, actually, and that's why I referred to it as kind of a vicious cycle and a trap, really, that communities get into. We think happens is that both are important. It's hard to say it's just this. So you get a cycle whereby you have high concentration of poverty and especially when it is related to particular groups. So for example in the United States, it's the case that African-Americans are disproportionately poor. But even if poor, they're much more likely than, let's say, a poor white to live in a poor neighborhood. And that's what we refer to as a concentration effect. That then leads to all sorts of other conditions. Businesses are less likely to invest. People may be fearful of the violence and as you note move out, which then may make things worse. So what we try to think about is how to intervene in that social system. But we do think, based on good evidence, that the characteristics of the communities do seem to have an independent effect. And likewise, fear among residents is a really important factor in - by the way, not just for moving out of a community, but fear is implicated in anxiety and other kinds of health-related issues.

**C.** distractor

> Yeah, you know, it's so funny that Jen calls with this comment because that is the very thing that I wanted to say to you, that if a person is overweight or obese, believe me, they're the first ones who know. They don't need anyone else telling them that. And yes, there are things that she can say to her family, like I know you want to help me. I know you're trying to help. But some of the ways in which you express the help is very hurtful. And nobody - people, these people, your family members are well-meaning. They think they're saying and doing the right thing. But because they don't walk in your shoes, have no idea of how painful some of those words can be to you and to others, you know, who must deal with this situation. So for your family and for all families listening, just know that to give helpful information like here's - I'm sorry, to give information like here's what I think might help, you know, it's - whether it's a meal plan, whether it's a lifestyle change, small incremental lifestyle changes that you feel a person can do without setting them up for failure, but - and without saying to them you're fat, or it's just so embarrassing or whatever. You know, all of those kinds of thoughts are very painful. To express whatever the help, the way in which you wish to help your family member in a loving way is always going to win over the opposite.

**D.** distractor

> Well, the U.S. economy right now, if you were grading it at college or high school, is probably a B-plus in the sense that, yes, things are certainly recovering. But it's not dazzling. The one thing that's really clear, however, is that it's a lot better than the stock market crash over the last few days would actually indicate. Whether it spreads to the rest of the economy depends right now on what happens to that elusive issue of competence. Remember, the economy is not just about statistics. They're also about psychology. And if people start to feel so nervous about the future that consumers don't go out and buy that new washing machine or companies don't go out and create jobs then, yes, it certainly will start to spread to the real economy. And we have seen plenty of cases in history where that's happened before. But if investors simply shrug their shoulders and say, well, you know what? The stock markets are crazy. You know, we don't really trust the way they're operating, but, hey, it doesn't affect us, then actually this week's squall will end up seeming like a huge summer thunderstorm rather than a significant change in the season. We just don't know as of yet. But an awful lot depends as well on what happens next with the Federal Reserve and whether they raise rates or not.

**Entity-stripped variant of the true option (the A4.2 re-score):**

> That's an excellent question. That's one of the things that we've looked at in research. It's really hard to disentangle, actually, and that's why I referred to it as kind of a vicious cycle and a trap, really, that communities get into. We think happens is that both are important. It's hard to say it's just this. So you get a cycle whereby you have high concentration of poverty and especially when it is related to particular groups. So for example in the [NAME], it's the case that [NAME] are disproportionately poor. But even if poor, they're much more likely than, let's say, a poor white to live in a poor neighborhood. And that's what we refer to as a concentration effect. That then leads to all sorts of other conditions. Businesses are less likely to invest. People may be fearful of the violence and as you note move out, which then may make things worse. So what we try to think about is how to intervene in that social system. But we do think, based on good evidence, that the characteristics of the communities do seem to have an independent effect. And likewise, fear among residents is a really important factor in - by the way, not just for moving out of a community, but fear is implicated in anxiety and other kinds of health-related issues.

### `C02006:NPR-14829:19`  (57 words, relaxation rung 0)

**QUESTION**

> (Laughter) The gist of your tweet, essentially, was your country is in a lot of trouble because of that stupid, bloody referendum. What do you mean?

**A.** distractor

> It was a country that was simply not functioning. The banks were all closed. The Central Bank of Iraq had been looted. The ministries had been figuratively and literally destroyed. Only the Ministry of Oil was effectively protected. And there was no governance and no infrastructure that was functioning, and thus, the rebuilding program you might say, started the country up from scratch.

**B.** distractor

> Well, I think the only way we can judge - the same we did in the past - is judging him by his actions. And Prime Minister Netanyahu did not take any substantive step to show the Palestinian people that he is serious about ending his occupation of the Palestinian people and reaching a political resolution to the conflict.

**C.** **TRUE ANSWER**

> Well, you know, it was a great mistake to muddle two systems of government. You know, we have a representative democracy. We elect MPs. And the MPs go into the House of Commons. And they choose the laws. We had a referendum, a plebiscite, which overruled Westminster's power. And we have been in a mess ever since.

**D.** distractor

> So when he first won in 1997 at the Masters at Augusta National, his father was waiting for him right off of the 18th green. And Tiger was 21 years old at that point. And it was really a culmination of a journey between a father and a son in shocking the world and becoming the youngest Masters champion of all time and the first African-American champion.

**Entity-stripped variant of the true option (the A4.2 re-score):**

> Well, you know, it was a great mistake to muddle two systems of government. You know, we have a representative democracy. We elect [NAME]. And the [NAME] go into the [NAME] of [NAME]. And they choose the laws. We had a referendum, a plebiscite, which overruled [NAME] power. And we have been in a mess ever since.

## 3. The rendered prompts

One `twin_redacted` prompt in full — the primary arm, and the owner deliverable — then the first 40 lines of one prompt from each other arm. All five are the SAME item, so the arms differ only by what D8 says they differ by.

### 3.1 `twin_redacted` (PRIMARY), item `C02124:NPR-12184:2`, standard options — complete and verbatim

```
Below are excerpts from past interviews with one person, called GUEST here. Read them, then answer as GUEST would in a later interview.

PAST INTERVIEWS
[Interview, 2012-06-14, Talk of the Nation]
HOST: As you pointed out, the Supreme Constitutional Court is a holdover from the Mubarak regime. Will they be grandfathered in in the new constitution? Will they continue to be the highest court in the land?
GUEST: Well, to be fair, and hopefully not pedantic, under the previous regime, they were thought to have a significant degree of independence, and, in fact, overruled Mr. Mubarak's laws on a number of occasions. Nevertheless, however, again if you think a revolution is significant political change with regard to institutions in government and so on, then there has to be some thinking about what the composition of the Supreme Constitutional Court is going to be, whether the head of it is going to be, you know, a leftover from the Mubarak regime, which is the case, and so on. So yes, there has to be change in all institutions of government, including the judiciary.

HOST: And the military, one would think a constitution would put - as we think of it - civilian authorities in charge of the military. Is that likely to happen now?
GUEST: You would think so. You would hope so. You can't have a democracy without civilian control of the military. But unfortunately, this leftover, holdover from the Mubarak regime is incredibly powerful, and I think we're likely to see some authority, some provisions accorded to them. I don't think we're going to see a civilian as the minister of defense in the next few years.

HOST: As you look ahead to the situation just over the next few days, clearly there are already reports of crowds gathering in Tahrir Square, as you might expect. Last night, the military supreme council gave troops the authority to arrest civilians for a range of pretty vague crimes, ranging from jaywalking, I think, to obstructing traffic, and basically, they gave themselves the right to crack down if they wish to.
GUEST: Well, that's correct. And this is again, you know, undemocratic and trounces upon any conception of civil liberties and rule of law, I think. And that's why not only the human rights groups in Egypt, but many others are outraged that this was passed by the minister of justice. Of course in - hopefully, and this might be naive, that this will not be used to manipulate the election in one way or another, and hopefully on the 16th and 17th, democratic - as much as they can be - elections will take place. And someone will be elected, and hopefully that will not be a leftover from the Mubarak regime.

HOST: The scene as described by reporters in Cairo today, who sounded awfully ominous, with military vehicles cruising the streets and, over loudspeakers, playing patriotic songs. Boy, when you hear patriotic music being broadcast, that smells coup to me.
GUEST: Yes. Well, you know, there weren't any people taken hostage or held up in the presidential palace - since they don't have a president - and so on. So, you know, I can understand where people are coming from with regard to the soft coup. But, of course, there are some - and again, I don't think complete or enough - but there are some legal bases for the rulings of the Supreme Constitutional Court. Again, I think this is a mess, incredibly convoluted and complicated. The supreme council has mismanaged and been malicious in its management of affairs since Mubarak's ouster on February 11th, and Egypt hasn't witnessed a real revolution that means fundamental change in the political institutions, let alone, you know, the distribution of economic power in society. We still have very powerful elements of the Mubarak regime in place that, if not completely calling the shots, are definitely wielding significant power and trying to direct things in a certain way.

HOST: And where does this leave the secular Egyptians - who a lot of people gave credit for starting all of this back, what, 16, 18 months ago - where does it leave them? They were given the choice between an authoritarian, Mr. Shafiq, and a member of the Muslim Brotherhood.
GUEST: Well, you know, many of the youth who were behind the revolution, as well as the supposed liberals and secular forces, are really having a difficult time right now. They see the choice in front of them as between worse and terrible. And some are holding their nose and voting, or going to vote for the Muslim Brotherhood candidate, because he represents some kind of change. Others who prioritize the idea of a secular state or a civil state are holding their nose and going to choose Shafiq, Mr. Mubarak's last prime minister. And a significant number of them have actually called for either a boycott of the election, or going and voting and invalidating their votes. And we've already seen significant numbers of that in the expatriate voting that has already taken place across the world.

HOST: GUEST, thank you very much for your time today. Appreciate it.
GUEST: My pleasure.

[Interview, 2012-11-24, All Things Considered]
HOST: I'm joined now by GUEST, professor of Middle East politics at Georgetown University. Welcome to you.
GUEST: Thank you.

HOST: So Mohammed Morsi was widely praised for his role in negotiating the cease-fire between Israel and Hamas this last week. And now he appears to be playing the same role on the international stage as his predecessor, Hosni Mubarak, and I mean by that, being an autocrat at home while being an international statesman.
GUEST: Well, that's certainly the charge by many in Egypt, and there are legitimate reasons for that charge because the new constitutional declaration gives him incredibly wide-ranging powers at a time when Egypt lacks legislature. There's no parliament right now because it was dissolved, and he has legislative powers in addition to executive powers. But now he's taken some judicial powers as well in a nondemocratic move. And that's worrying many people in Egypt, particularly liberals and secular voices.

HOST: It was, of course, this last year that we saw all the demonstrators in Tahrir Square and all over Egypt. What does it mean for the democracy movement that we've followed so closely?
GUEST: Well, it means that the transition to democracy in Egypt is certainly not guaranteed, and the best we can say about it is that it's a mess. It has not been orderly. There has not been a process that has achieved consensus with regard to a constitution, elections and so on. And there are concerns by many that the Muslim Brotherhood is now attempting to exert greater control over the political process, possibly dominating the political process at the expense of the original goals of the revolution.

HOST: Mohammed Morsi's election this year in June raised some concerns that after the Arab Spring that there would be a way that Islamist governments in the region, that that would make things even more unstable. Do you think that's what we're seeing?
GUEST: Well, it's not exactly what we're seeing. I mean, it's certainly after the uprisings in the Arab world - in Tunisia, in Egypt, in Yemen and elsewhere - which were initially voiced in a language of democracy and freedoms and so on, Islamists naturally did well. And I think those of us who know the region would expect that. Islamists have been the most powerful political force over the last 30 or 40 years. And when there were elections, Islamists succeeded. The question is, are those Islamists who are committed to democracy - I think that's clear in Tunisia and Egypt - are they committed to democracy where minorities are guaranteed equal rights and citizenship as those in the majority? And I think many of us in Egypt are at least questioning that to some extent.

HOST: You're Egyptian. I want to also ask you, what do you make of the timing of this? I mean, one day, he's being the peace broker between Israel and Hamas, and then the next day, this decree. Anything we should read there?
GUEST: Well, it's not clear, but it would seem, if one was cynical that it's incredibly opportunistic. Mr. Morsi certainly was at a zenith in terms of popularity and certainly in the international community. He received praise from Secretary Clinton, from Mr. Netanyahu, from Khaled Mashaal of the Hamas and Egyptian people. And then immediately afterwards, he takes these measures. So I think some people are legitimately skeptical about the timing of these constitutional declarations.

HOST: What's most worrisome to you as you - I know you've only had a few days, but what's most worrisome to you in the Morsi edict?
GUEST: What's most worrisome to me is the fact that the constituent assembly, which is dominated by members of the Muslim Brotherhood and the Salafis does not represent - I would say a consensus opinion among Egyptians, which, of course, is what a constituent assembly and the constitution should do - is now immune from any kind of judicial challenge or appeal. And that's worrisome because, I think, Egyptians do not want a document as a constitution that is catered or geared to one particular view and that doesn't guarantee rights for women, religious minorities, political dissent and so on.

HOST: GUEST teaches Middle East politics at Georgetown University. Thanks very much for coming in.
GUEST: My pleasure.

[Interview, 2013-07-06, All Things Considered]
HOST: I spoke with them both a short while ago and began by asking GUEST about the paradox that country now faces.
GUEST: Well, the paradox is that we have a supposedly democratic movement, which does believe in many of the principles of democracy and so on that have called on the military to oust a democratically elected leader so that democracy can be established or put on the right path. That's the paradox. I understand the difficulties that Egypt went through and is going through and is going to deal with in the coming days and months and years. At the same time, I think we can't lose sight of the fact that on June 30th and the days afterwards, millions and millions of Egyptians went out onto the streets and called for the end of Mr. Morsi's presidency. Although, of course, I did not imagine or welcome military removal of democratically elected president, I think referring to this simply as a military coup without any other adjectives does damage to our understanding of the complexity of the situation.

HOST: Well, beyond religious issues, GUEST, how do basic economic issues factor into the crisis we're seeing now in Egypt?
GUEST: Well, I think there's no question that that was a large component of it. The economy has been spiraling downwards with increasing unemployment, fuel shortages, bread shortages, labor strikes and an inability to secure an IMF loan, increasing borrowing, deteriorating exchange rate. And so this certainly contributed to outrage at Mr. Morsi and the Muslim Brotherhood. Many of his promises were unmet.

HOST: So what about the United States' role in all of this? GUEST, would you say we're in kind of an awkward spot right about now? After all, it was just two months ago that Secretary of State John Kerry approved $1.3 billion in annual U.S. military aid to Egypt. So now with the ousting of Mr. Morsi, many are questioning whether the United States should continue that aid. What do you think?
GUEST: Well, I think that the United States will likely continue the aid if the White House and the administration has a say in the matter. I don't think you're going to get many people in the Obama administration referring to this as a coup. Now, there are larger and, in fact, maybe more important questions that should be asked with regard to U.S. aid to Egypt. And that is, is the $1.3 billion going to benefit the vast majority of Egyptians in things that the country needs the most: education, health care, infrastructure? Or is it going to support a military, which is really where the vast majority of funds go in order to buy a pliant relationship and to maintain the Egyptian-Israeli peace accords and so on.

A LATER INTERVIEW
HOST: Why is a field marshal, according to various surveys, so popular in Egypt?

Which of these replies did GUEST give?
A. With any luck, they face - you know, they have to face the - they have to face the voters. Once these things are known, I believe there is a difference between people who are elected with knowledge of this and people who are elected without knowledge of this, like Franken. And the Kihuen situation goes to what we were just talking about.
B. I think it is. I think the fact that it was such a sort of randomized event and so many - so many lives could have been lost, it really changes the context. I mean, if you think about Unabomber, who killed the same number of people and injured, I believe, fewer than 25 - and his venue was changed. So the fact that this one is not is very interesting to me professionally.
C. It shouldn't be. But for bishops to defend LGBT people or put themselves out on the line for LGBT people is rather rare. And so one of the things that I try to do in the book is point to bishops and cardinals, in some cases, who are out there and who are supporting their LGBT brothers and sisters and siblings.
D. He's popular for a number of reasons. One, there were many people, of course, who were opposed to the Muslim Brotherhood and Mr. Morsi before he became president. And of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.

Give a probability for each option, summing to 1. End your reply with one line in exactly this format and nothing after it:
A: 0.25 B: 0.25 C: 0.25 D: 0.25
```

### 3.2 `twin_named`, same item — first 40 lines

```
Below are excerpts from past interviews with one person, called GUEST here. Read them, then answer as GUEST would in a later interview.

GUEST is Samer Shehata.

PAST INTERVIEWS
[Interview, 2012-06-14, Talk of the Nation]
HOST: As you pointed out, the Supreme Constitutional Court is a holdover from the Mubarak regime. Will they be grandfathered in in the new constitution? Will they continue to be the highest court in the land?
GUEST: Well, to be fair, and hopefully not pedantic, under the previous regime, they were thought to have a significant degree of independence, and, in fact, overruled Mr. Mubarak's laws on a number of occasions. Nevertheless, however, again if you think a revolution is significant political change with regard to institutions in government and so on, then there has to be some thinking about what the composition of the Supreme Constitutional Court is going to be, whether the head of it is going to be, you know, a leftover from the Mubarak regime, which is the case, and so on. So yes, there has to be change in all institutions of government, including the judiciary.

HOST: And the military, one would think a constitution would put - as we think of it - civilian authorities in charge of the military. Is that likely to happen now?
GUEST: You would think so. You would hope so. You can't have a democracy without civilian control of the military. But unfortunately, this leftover, holdover from the Mubarak regime is incredibly powerful, and I think we're likely to see some authority, some provisions accorded to them. I don't think we're going to see a civilian as the minister of defense in the next few years.

HOST: As you look ahead to the situation just over the next few days, clearly there are already reports of crowds gathering in Tahrir Square, as you might expect. Last night, the military supreme council gave troops the authority to arrest civilians for a range of pretty vague crimes, ranging from jaywalking, I think, to obstructing traffic, and basically, they gave themselves the right to crack down if they wish to.
GUEST: Well, that's correct. And this is again, you know, undemocratic and trounces upon any conception of civil liberties and rule of law, I think. And that's why not only the human rights groups in Egypt, but many others are outraged that this was passed by the minister of justice. Of course in - hopefully, and this might be naive, that this will not be used to manipulate the election in one way or another, and hopefully on the 16th and 17th, democratic - as much as they can be - elections will take place. And someone will be elected, and hopefully that will not be a leftover from the Mubarak regime.

HOST: The scene as described by reporters in Cairo today, who sounded awfully ominous, with military vehicles cruising the streets and, over loudspeakers, playing patriotic songs. Boy, when you hear patriotic music being broadcast, that smells coup to me.
GUEST: Yes. Well, you know, there weren't any people taken hostage or held up in the presidential palace - since they don't have a president - and so on. So, you know, I can understand where people are coming from with regard to the soft coup. But, of course, there are some - and again, I don't think complete or enough - but there are some legal bases for the rulings of the Supreme Constitutional Court. Again, I think this is a mess, incredibly convoluted and complicated. The supreme council has mismanaged and been malicious in its management of affairs since Mubarak's ouster on February 11th, and Egypt hasn't witnessed a real revolution that means fundamental change in the political institutions, let alone, you know, the distribution of economic power in society. We still have very powerful elements of the Mubarak regime in place that, if not completely calling the shots, are definitely wielding significant power and trying to direct things in a certain way.

HOST: And where does this leave the secular Egyptians - who a lot of people gave credit for starting all of this back, what, 16, 18 months ago - where does it leave them? They were given the choice between an authoritarian, Mr. Shafiq, and a member of the Muslim Brotherhood.
GUEST: Well, you know, many of the youth who were behind the revolution, as well as the supposed liberals and secular forces, are really having a difficult time right now. They see the choice in front of them as between worse and terrible. And some are holding their nose and voting, or going to vote for the Muslim Brotherhood candidate, because he represents some kind of change. Others who prioritize the idea of a secular state or a civil state are holding their nose and going to choose Shafiq, Mr. Mubarak's last prime minister. And a significant number of them have actually called for either a boycott of the election, or going and voting and invalidating their votes. And we've already seen significant numbers of that in the expatriate voting that has already taken place across the world.

HOST: GUEST, thank you very much for your time today. Appreciate it.
GUEST: My pleasure.

[Interview, 2012-11-24, All Things Considered]
HOST: I'm joined now by GUEST, professor of Middle East politics at Georgetown University. Welcome to you.
GUEST: Thank you.

HOST: So Mohammed Morsi was widely praised for his role in negotiating the cease-fire between Israel and Hamas this last week. And now he appears to be playing the same role on the international stage as his predecessor, Hosni Mubarak, and I mean by that, being an autocrat at home while being an international statesman.
GUEST: Well, that's certainly the charge by many in Egypt, and there are legitimate reasons for that charge because the new constitutional declaration gives him incredibly wide-ranging powers at a time when Egypt lacks legislature. There's no parliament right now because it was dissolved, and he has legislative powers in addition to executive powers. But now he's taken some judicial powers as well in a nondemocratic move. And that's worrying many people in Egypt, particularly liberals and secular voices.

HOST: It was, of course, this last year that we saw all the demonstrators in Tahrir Square and all over Egypt. What does it mean for the democracy movement that we've followed so closely?
GUEST: Well, it means that the transition to democracy in Egypt is certainly not guaranteed, and the best we can say about it is that it's a mess. It has not been orderly. There has not been a process that has achieved consensus with regard to a constitution, elections and so on. And there are concerns by many that the Muslim Brotherhood is now attempting to exert greater control over the political process, possibly dominating the political process at the expense of the original goals of the revolution.

HOST: Mohammed Morsi's election this year in June raised some concerns that after the Arab Spring that there would be a way that Islamist governments in the region, that that would make things even more unstable. Do you think that's what we're seeing?
GUEST: Well, it's not exactly what we're seeing. I mean, it's certainly after the uprisings in the Arab world - in Tunisia, in Egypt, in Yemen and elsewhere - which were initially voiced in a language of democracy and freedoms and so on, Islamists naturally did well. And I think those of us who know the region would expect that. Islamists have been the most powerful political force over the last 30 or 40 years. And when there were elections, Islamists succeeded. The question is, are those Islamists who are committed to democracy - I think that's clear in Tunisia and Egypt - are they committed to democracy where minorities are guaranteed equal rights and citizenship as those in the majority? And I think many of us in Egypt are at least questioning that to some extent.

HOST: You're Egyptian. I want to also ask you, what do you make of the timing of this? I mean, one day, he's being the peace broker between Israel and Hamas, and then the next day, this decree. Anything we should read there?
GUEST: Well, it's not clear, but it would seem, if one was cynical that it's incredibly opportunistic. Mr. Morsi certainly was at a zenith in terms of popularity and certainly in the international community. He received praise from Secretary Clinton, from Mr. Netanyahu, from Khaled Mashaal of the Hamas and Egyptian people. And then immediately afterwards, he takes these measures. So I think some people are legitimately skeptical about the timing of these constitutional declarations.


[... truncated, 27 more lines ...]
```

### 3.3 `zeroinfo_redacted`, same item — first 40 lines

```
A person was interviewed on American broadcast news. Predict which answer they gave. The person is called GUEST in the question below.

HOST: Why is a field marshal, according to various surveys, so popular in Egypt?

Which of these replies did the person give?
A. With any luck, they face - you know, they have to face the - they have to face the voters. Once these things are known, I believe there is a difference between people who are elected with knowledge of this and people who are elected without knowledge of this, like Franken. And the Kihuen situation goes to what we were just talking about.
B. I think it is. I think the fact that it was such a sort of randomized event and so many - so many lives could have been lost, it really changes the context. I mean, if you think about Unabomber, who killed the same number of people and injured, I believe, fewer than 25 - and his venue was changed. So the fact that this one is not is very interesting to me professionally.
C. It shouldn't be. But for bishops to defend LGBT people or put themselves out on the line for LGBT people is rather rare. And so one of the things that I try to do in the book is point to bishops and cardinals, in some cases, who are out there and who are supporting their LGBT brothers and sisters and siblings.
D. He's popular for a number of reasons. One, there were many people, of course, who were opposed to the Muslim Brotherhood and Mr. Morsi before he became president. And of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.

Give a probability for each option, summing to 1. End your reply with one line in exactly this format and nothing after it:
A: 0.25 B: 0.25 C: 0.25 D: 0.25
```

### 3.4 `zeroinfo_named`, same item — first 40 lines

```
A person was interviewed on American broadcast news. Predict which answer they gave. The person is called GUEST in the question below.

The person is Samer Shehata.

HOST: Why is a field marshal, according to various surveys, so popular in Egypt?

Which of these replies did the person give?
A. With any luck, they face - you know, they have to face the - they have to face the voters. Once these things are known, I believe there is a difference between people who are elected with knowledge of this and people who are elected without knowledge of this, like Franken. And the Kihuen situation goes to what we were just talking about.
B. I think it is. I think the fact that it was such a sort of randomized event and so many - so many lives could have been lost, it really changes the context. I mean, if you think about Unabomber, who killed the same number of people and injured, I believe, fewer than 25 - and his venue was changed. So the fact that this one is not is very interesting to me professionally.
C. It shouldn't be. But for bishops to defend LGBT people or put themselves out on the line for LGBT people is rather rare. And so one of the things that I try to do in the book is point to bishops and cardinals, in some cases, who are out there and who are supporting their LGBT brothers and sisters and siblings.
D. He's popular for a number of reasons. One, there were many people, of course, who were opposed to the Muslim Brotherhood and Mr. Morsi before he became president. And of course it was a disastrous year in office. And there are many people who, as a result of all of that, are longing for stability and security. And the idea of a military general running the show is reassuring.

Give a probability for each option, summing to 1. End your reply with one line in exactly this format and nothing after it:
A: 0.25 B: 0.25 C: 0.25 D: 0.25
```

### 3.5 `imposter_redacted`, same item — first 40 lines

```
Below are excerpts from past interviews with one person, called GUEST here. Read them, then answer as GUEST would in a later interview.

PAST INTERVIEWS
[Interview, 2013-06-05, Talk of the Nation]
HOST: And someone have described it as a majoritarian dictatorship.
GUEST: Well, certainly, although Prime Minister Erdogan doesn't actually enjoy a majority, he got 49.95 percent of the vote. But I guess that's as close as you're going to get. But, indeed, there is a sense that the prime minister and the government rule with very little regard to half the country that disagrees with their view of the world and their policies. He governs half the country and intimidates the rest, and we saw that on full display in his responses to the protests in Taksim Square or Ankara or Izmir or some of the other cities where there had been pretty significant protests by calling them - as you pointed out, the protesters calling them thugs, alcoholics, extremists and so on and so forth.

HOST: Yet this is also - the prime minister, Erdogan, under his leadership the country has enjoyed an immense burst of prosperity.
GUEST: That's absolutely the case. Turkey is the 16th or, by another measure, 17th largest economy in the world. Turks are wealthier than they've been in the past. And that is part of the secret to Erdogan's success. And that is why if there was an election today, I think there's no doubt that Prime Minister Erdogan would win. Perhaps he wouldn't get 49.95 percent of the vote, but he would certainly get a very large number of votes. There is a growing middle class of people who vote on one issue and one issue only, and that's on their pocketbooks. Add that to a core constituency and the fact that the opposition parties are extraordinarily weak, don't have much to offer Turks in the way a positive vision for Turkey's future, and Prime Minister Erdogan, despite this being the greatest political crisis of his decade at power, would still prevail.

HOST: Give us an idea of who is at these demonstrations, which groups. Are these the disaffected, the people who voted against him, the people who lost the last election, as he puts it?
GUEST: It's certainly those people. There has been a contingent of secular urban but not all elite people who've come out who have felt hemmed in and marginalized over the course of the last decade. And they're - because their parties have been so ineffective in challenging the Justice and Development Party, they are now finding their voices in the street. Prime Minister Erdogan has wanted to finger the main opposition party, the Republican People's Party, for the demonstrations. That's certainly not the case. It's not out there as a party, although there are supporters of that party in the street. But there are many others as well. I think the kind of polling already that's been done of who's in Taksim Square shows that a majority of these people are secular-minded and that they oppose the Justice and Development Party. But there are also some, a smattering of people, who had supported the party in the past. Primarily those are liberals who had determined that the other parties offered them nothing and threw their lot in with the Justice and Development Party, only to find that Prime Minister Erdogan had gone back on his words about a consolidated liberal democracy. But one more thing: I think it would be a mistake to pit this as secularists versus Islamists. I think the demands of people in the streets to the extent that you can characterize them are about this authoritarian or illiberal turn in Turkish politics. Many of them say they just - they want their freedom. They want democracy. They want to have a voice in the political system.

HOST: And is it fair to say that some of them are - let me put this another way. You cited there was a plot against the Erdogan government some years ago by elements within the military, among others the so-called deep state in Turkey that was used by the prime minister, this plot, to justify a number of actions since then. Is he going to use, do you think, this new crisis the same way?
GUEST: Well, if past precedent is any measure, there is certainly the possibility that the prime minister does not come out of this crisis once it's defused in a way that is more pragmatic or conciliatory, but in fact that he may seek to crack down on these elements that have gone out into the streets. This is someone who has in the past not demonstrated a capacity for contrition. So it certainly is a possibility. The problem right now is, is that the authorities have been unable to defuse the protests, and that's primarily because Erdogan himself has not gone out and made conciliatory words, although deputies of his has. I think that people are waiting for Erdogan to make a move and to hopefully calm the streets, and then Turkey can kind of re-evaluate where their next steps are, where Turks, their next steps are in terms of politics. But there's really no evidence that suggests that Erdogan is willing to do that.

HOST: Twenty years ago, demonstrations this size, we would be waiting for the military to step in and say, wait a minute, things are getting out of control. We're going to have to take charge here.
GUEST: That's true. Turkey had a history of coups d'etat in 1960, 1971, 1980 and again in 1997. And then beyond, under the threshold of a coup, the military was influential in a variety of ways in politics and played a very, very powerful role in the politics of the country. Beginning in 2003 and 2004, the Justice and Development Party had begun to bring the military under civilian control, which is overall a good thing. It helps create an environment to the emergence of a more democratic Turkey. And since the revelation of this plot, they have gone after the military through the court system, and there are many retired and currently serving officers serving prison terms as a result. So the military's wings have been more than clipped. They don't have the capacity any longer to get involved in politics. The days when Turkish governments were brought down by the military are over. A changed in - at the prime ministry is going to come by the ballot box.

HOST: By the ballot box and not by the demonstrations in the street either.
GUEST: This is not the Turkish analog of the Egyptian uprising. As I said, Turkish political institutions have been - some of them, at least, have been hollowed out by the actions of the Justice and Development Party, but one thing that's been strong throughout the days of coups and returns to civilian control dating back to the mid-1940s, there has been a multi-party political system in which parties could contest elections. And those elections have been free and fair. And the expectation is that that is the way - the expectation of Turks, that is the way in which to change governments.

HOST: And this description of this hollow democracy, as you describe it, then brings us to the example, the model of Turkey, which has been held out to the newly emerging governments in Egypt, in Libya and in other places as this is the way toward a Islamic democracy.
GUEST: Indeed. It seem that once the Justice and Development Party came to power in 2002 and undertook these broad-ranging political reforms that here was an example of a Muslim majority country, an Islamist political party accumulating power, exercising that power in a officially secular political order. And to boot, they were successful economically. And I think that many people in the Arab World see Turkey and understand that it has much to offer them. But the problem is just at the time that - not just the United States, but others were holding out Turkey as a model or inspiration for the Arab World - was when this process of hollowing out Turkey's democratic institutions begin, and that this illiberal drift in the Turkish - in Turkish politics was getting underway, yet people continue to hold out the Turkish model. This is certainly not what people in the Arab World initially rose up against - rose up for. Turkey is certainly better than Egypt or Tunisia or Libya. But some of the things that Prime Minister Erdogan and the party have done are, in fact, reminiscent of the authoritarian moves that dictators in the Middle East had undertaken during their times in office.

HOST: And this revision of the constitution, many believe that Prime Minister Erdogan wants a constitution that will allow him to be a much more powerful Turkish president.
GUEST: That's exactly right. This has been a cause celebre in Turkey whether or not the Justice and Development Party will respect the interparliamentary committee that is drafting a new constitution, or will they try to go around this committee, which they take part in, and table their own constitution that has been written specifically to allow for a more powerful presidency that ultimately Prime Minister Erdogan would occupy that office, and he would exercise a range powers that the Turkish presidency does not have at - under the present configuration of powers in the country. And it would also allow him to stay in power for years to come.

HOST: And so as you look toward the future of Turkey, what lessons do you think the prime minister ought to derive from these demonstrations which are, as you suggest, the greatest challenge in his political career?
GUEST: You know, the prime minister during his first term in office between 2003 and 2007 was pragmatic, did seek consensus on important issues of the day. So it's clear that he has it within him. I think over the years the increasing, increasingly better electoral returns, a sort of detachment from the people, which is ironic because he made his political career on being close to the people - if he returns to that pragmatism, to that consensus building, if he understands somehow that in a democracy it is not just majority rules, that the voice and desires of the minority deserve a hearing as well, it will certainly put Turkey on a better path. But again, based on recent events, it's unclear that he is able to do that, which is a concern about the future path for Turkey's politics.

HOST: And in terms of the United States, the prime minister has enjoyed a close relationship with President Obama. In recent days, American officials have called for restraint by Turkish forces against the protesters. But this is a country on whom the United States leans for help with Syria and with Iran as well.
GUEST: It goes without saying that Turkey throughout has been a strong partner and a strategic ally of the United States. There is not an issue - an important issue in American foreign policy in that part of the world that Turkey is not involved in or touches on in either direct or indirect ways. And I think that's why the administration has been somewhat reluctant previously to call Erdogan out on, for example, freedom of the press and freedom of expression. But at the same time, we should be able to work with a strategic partner and at least politely point out that the reversals in Turkey's democratic transition is not good for Turkey and not good for the strategic relationship.

HOST: GUEST, thanks very much for your time, as always.
GUEST: My pleasure.

HOST: GUEST wrote the piece "How Democratic Is Turkey?" It ran in Foreign Policy. Again, there's a link to it at npr.org. He joins us today from a studio at the Council on Foreign Relations.
GUEST: Tomorrow, an inside look at the lives of animators, and our favorite film buff, Murray Horwitz, joins us to talk about robot movies. If you'd like to nominate your favorite, send us an email, talk@npr.org, then join us tomorrow on TALK OF THE NATION from NPR News.


[... truncated, 11 more lines ...]
```

## 4. The follow-up classifier

Rubric `RUBRIC_V1`, sha256 `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da`, frozen and pinned by a test. **The classifier prompts are deliberately not redacted** — rationale in finding 8.10.

469 model cases and 271 rule-labelled turns (a host turn with no guest answer anywhere behind it is NEW-TOPIC by definition and costs no model call). Parse-failure rate **0.0000**.

### 4.1 The rubric, verbatim

```
FOLLOW-UP OR NEW-TOPIC

Label one turn from a news interview. Each case gives three fields:

PREV: the interviewer's previous turn.
GUEST: what the guest said in reply to PREV.
TARGET: the interviewer turn you must label.

A field may be cut off mid-sentence; "..." marks removed text. Label the TARGET
only.

FOLLOW-UP means the TARGET references, quotes, probes, or challenges something
in GUEST. That includes minimal continuers that only ask for more of the same
answer ("Go on.", "Meaning what?", "Such as?"); asking the guest to explain,
define, or back up something they just said; and pushback that disputes it.

NEW-TOPIC means the TARGET brings in material that does not come from GUEST: a
prepared or agenda question, a change of subject, a segment transition, a
sign-off, or a question to someone else. Two turns that look like follow-ups
but are NEW-TOPIC: acknowledge-then-pivot ("Fascinating. Now, the budget
vote..."), and going back to the interviewer's own earlier line of questioning
as if GUEST had not happened.

HARD CASES
1. Compound turn (a comment or acknowledgment plus a question): label by the
question. Probes GUEST -> FOLLOW-UP. New material -> NEW-TOPIC.
2. Same topic is not enough: a question can share the subject and still be
NEW-TOPIC if it takes nothing from GUEST.
3. Re-asking something the guest dodged is FOLLOW-UP only if the TARGET names
the dodge or quotes the answer; a bare repeat is NEW-TOPIC.
4. Part taken from GUEST and part new -> FOLLOW-UP.
5. Judge the words, not the interviewer's intention.

EXAMPLES

PREV: Why did you resign that week?
GUEST: I asked for the audit three times and was told to wait. After the third refusal I quit.
TARGET: Go on.
LABEL: FOLLOW-UP
WHY: A bare prompt to keep talking asks for more of the same answer.

PREV: How bad is the shortage?
GUEST: We are down to one week of supply and have started rationing tests.
TARGET: That is alarming. Who decides which patients get tested?
LABEL: FOLLOW-UP
WHY: The comment is filler; the question digs into the rationing just described.

PREV: How bad is the shortage?
GUEST: We are down to one week of supply and have started rationing tests.
TARGET: Fascinating. Let me turn to the election - will you endorse the governor?
LABEL: NEW-TOPIC
WHY: The acknowledgment is followed by a pivot to unrelated material.

PREV: Do you think your party mishandled the vote?
GUEST: I would not put it that way. The vote was rushed, and members said so afterwards.
TARGET: Earlier I asked about the housing bill. Are you still voting for it?
LABEL: NEW-TOPIC
WHY: The interviewer returns to an earlier question and uses nothing from the answer.
```

### 4.2 Per-subject label counts

| subject | FOLLOW-UP | NEW-TOPIC | parse failures | rule labels (NEW-TOPIC) |
|---|---|---|---|---|
| C00292 | 67 | 100 | 0 | 163 |
| C00792 | 27 | 49 | 0 | 6 |
| C01677 | 19 | 33 | 0 | 53 |
| C02006 | 10 | 8 | 0 | 2 |
| C02013 | 11 | 14 | 0 | 5 |
| C02124 | 39 | 92 | 0 | 42 |

### 4.3 20 sampled classifications (seeded, seed 49; spread across subjects first)

| subject | transcript | turn | label | target turn (truncated) | model's WHY |
|---|---|---|---|---|---|
| C00292 | CNN-6039 | 48 | FOLLOW-UP | What does it all mean? Is there like a big pie chart of who's doing what? What's the political implication? | The target asks for the meaning and implications of the organization plan mentioned in the previous turns. |
| C02006 | NPR-37430 | 2 | FOLLOW-UP | Robert Harris is reading from his book, “Imperium,” which is a novel about the Roman Empire. And if you think this language sounds like a description… | The target references the specific language used in the guest's reading to introduce a related quote. |
| C02124 | NPR-32351 | 13 | FOLLOW-UP | If the Muslim Brotherhood does gain a majority in these in these parliamentary elections, does that then set them up for a confrontation with the mili… | The target probes the consequences of the guest's statement regarding the Muslim Brotherhood's expected success in the elections. |
| C02013 | NPR-6056 | 9 | FOLLOW-UP | Mm-hmm. | The target is a minimal continuer prompting the guest to elaborate on the reasons they began listing. |
| C01677 | NPR-11032 | 56 | FOLLOW-UP | And therefore provide more time for talks. | The target summarizes and extends the guest's point about buying time for negotiations. |
| C00792 | NPR-6779 | 39 | FOLLOW-UP | My understanding is that if it is deployed, there is very little time to respond. | The target references the deployment of weaponry mentioned in the guest's response. |
| C00292 | CNN-5214 | 79 | FOLLOW-UP | There's a lot more smuggling. James, the vice admiral was here - big time guy - the coordinator of the forces there in the Gulf. | The target references the smuggling mentioned by the guest before introducing a new speaker to discuss it. |
| C00292 | CNN-3812 | 62 | FOLLOW-UP | He says with the ceiling lifted, you can't get the - the parts are not there. | The target provides further detail and evidence regarding the "deplorable conditions" mentioned in the previous turn. |
| C02124 | NPR-33910 | 4 | FOLLOW-UP | The former president of Tunisia, of course. | The target references and clarifies "Ben Ali," whom the guest just mentioned. |
| C02124 | NPR-33809 | 6 | FOLLOW-UP | Do you think that is the kind of democracy that people are really talking about? | The target probes the guest's specific claim that liberal democracy is the only kind that matters. |
| C00792 | NPR-6779 | 107 | NEW-TOPIC | We're talking about the conflict in Syria, and you're listening to TALK OF THE NATION, from NPR News. Let's go to Malas(ph) in Detroit. Hi, Malas. | The target is a segment transition and a pivot to a new caller. |
| C02006 | NPR-37430 | 16 | NEW-TOPIC | I wonder about an event in your own country, when it was seen as the leading nation in the world in the 1770s. In 1776, as a matter of fact, in Englan… | The interviewer pivots from the guest's points about the US to a new topic regarding Edward Gibbon and 18th-century England. |
| C02124 | NPR-30384 | 9 | NEW-TOPIC | You're Egyptian. I want to also ask you, what do you make of the timing of this? I mean, one day, he's being the peace broker between Israel and Hamas… | The interviewer pivots from the guest's discussion on democracy and minorities to a new question about the timing of a specific decree. |
| C00292 | CNN-21018 | 39 | NEW-TOPIC | All right. We have to move on to another very sticky issue on the agenda this week, which is the observer force in the Middle East. And, James, what's… | The interviewer explicitly pivots to a new agenda item regarding the observer force in the Middle East. |
| C01677 | NPR-12784 | 40 | NEW-TOPIC | Our number is 800-989-8255. Our email address is talk@npr.org. And you can also join the conversation at our website. Go to npr.org, and click on TALK… | The target is a sign-off and introduction of guests, which is a segment transition. |
| C02013 | NPR-6056 | 34 | NEW-TOPIC | Prof. SAMPSON. Yeah, exactly, and that goes to my last hypothesis, which I happen to think is the correct one, namely that we have a rapidly changing… | The interviewer introduces their own hypothesis and new research material regardless of the guest's brief agreement. |
| C00792 | NPR-6779 | 95 | NEW-TOPIC | Thanks for the call. | The target is a sign-off/acknowledgment to the caller and does not probe the guest's answer. |
| C02124 | NPR-2929 | 84 | NEW-TOPIC | I think what you see in the protests today, in Liberation Square, for instance, is in some ways a leaderless movement that is united around the unanim… | The interviewer introduces their own observation about the movement being leaderless rather than probing the guest's list of specific organizations. |
| C00292 | CNN-85004 | 44 | NEW-TOPIC | It's a lot quieter, sitting here at this table than being in the Green Zone in Baghdad, isn't it? | The target pivots from the legal discussion to a comment about the current physical environment. |
| C00292 | CNN-6671 | 76 | NEW-TOPIC | The issue of AIDS and the international community - a big controversy this week breaking out involving South African president Thabo Mbeki. James, wha… | The interviewer pivots to a completely different subject regarding AIDS and the South African president. |

Subjects represented: 6.

## 5. Accuracy per arm

> **STOP — read finding 8.0 before reading these tables.** The zero-information baseline scored **1.000 argmax accuracy**: a prompt with no excerpts, no name, no programme and no date got every item right. The item set is at ceiling, so the twin arms have nowhere to go, twin−zeroinfo lift is 0.00 by construction, and A4.3's filter empties every filtered cell. **These numbers say nothing about twin fidelity — they say the distractors are too easy.**

**Read every twin number against its zero-information baseline.** That is the project's standing rule and on this pilot it is the whole story, not a formality — see findings 8.0, 8.1 and 8.5. `N` counts records that PARSED; parse failures are excluded from both denominators and reported separately in 8.12.

### standard options, unfiltered

| arm | N scored | parse fails | argmax accuracy | prob-mass on correct |
|---|---|---|---|---|
| **twin_redacted** | 17 | 0 | 1.000 | 0.972 |
| twin_named | 17 | 0 | 1.000 | 0.985 |
| zeroinfo_redacted | 17 | 0 | 1.000 | 0.983 |
| zeroinfo_named | 17 | 0 | 1.000 | 0.991 |
| imposter_redacted | 17 | 0 | 0.941 | 0.885 |

### standard options, adversarial-filtered (A4.3)

Filter: A4.3: drop items zeroinfo_redacted got argmax-correct. **0 of 17 items survive.**

The zero-information arm solved every item, so the filter removes every item and there is nothing left to score. The empty table below is the correct output of a filter that is working; see finding 8.0.

| arm | N scored | parse fails | argmax accuracy | prob-mass on correct |
|---|---|---|---|---|
| **twin_redacted** | 0 | 0 | — | — |
| twin_named | 0 | 0 | — | — |
| zeroinfo_redacted | 0 | 0 | — | — |
| zeroinfo_named | 0 | 0 | — | — |
| imposter_redacted | 0 | 0 | — | — |

#### Lift rows (standard options)

Subject-paired mean differences. **No significance test, deliberately** — with 17 items over 5 subjects (one of them contributing a single item) the pilot is not powered for one, and a p-value here would invite exactly the reading this pilot cannot support. See finding 8.8.

*unfiltered*

| contrast | subjects paired | mean argmax delta | mean prob-mass delta |
|---|---|---|---|
| twin_redacted − zeroinfo_redacted | 5 | 0.000 | -0.006 |
| twin_redacted − imposter_redacted | 5 | 0.050 | 0.085 |

*adversarial filtered*

| contrast | subjects paired | mean argmax delta | mean prob-mass delta |
|---|---|---|---|
| twin_redacted − zeroinfo_redacted | 0 | — | — |
| twin_redacted − imposter_redacted | 0 | — | — |

### entity-stripped options (A4.2), unfiltered

| arm | N scored | parse fails | argmax accuracy | prob-mass on correct |
|---|---|---|---|---|
| **twin_redacted** | 17 | 0 | 1.000 | 0.970 |
| twin_named | 16 | 1 | 1.000 | 0.980 |
| zeroinfo_redacted | 17 | 0 | 1.000 | 0.958 |
| zeroinfo_named | 17 | 0 | 1.000 | 0.988 |
| imposter_redacted | 16 | 1 | 0.938 | 0.909 |

### entity-stripped options (A4.2), adversarial-filtered (A4.3)

Filter: A4.3: drop items zeroinfo_redacted got argmax-correct. **0 of 17 items survive.**

The zero-information arm solved every item, so the filter removes every item and there is nothing left to score. The empty table below is the correct output of a filter that is working; see finding 8.0.

| arm | N scored | parse fails | argmax accuracy | prob-mass on correct |
|---|---|---|---|---|
| **twin_redacted** | 0 | 0 | — | — |
| twin_named | 0 | 0 | — | — |
| zeroinfo_redacted | 0 | 0 | — | — |
| zeroinfo_named | 0 | 0 | — | — |
| imposter_redacted | 0 | 0 | — | — |

#### Lift rows (entity-stripped options (A4.2))

Subject-paired mean differences. **No significance test, deliberately** — with 17 items over 5 subjects (one of them contributing a single item) the pilot is not powered for one, and a p-value here would invite exactly the reading this pilot cannot support. See finding 8.8.

*unfiltered*

| contrast | subjects paired | mean argmax delta | mean prob-mass delta |
|---|---|---|---|
| twin_redacted − zeroinfo_redacted | 5 | 0.000 | 0.036 |
| twin_redacted − imposter_redacted | 5 | 0.050 | 0.055 |

*adversarial filtered*

| contrast | subjects paired | mean argmax delta | mean prob-mass delta |
|---|---|---|---|
| twin_redacted − zeroinfo_redacted | 0 | — | — |
| twin_redacted − imposter_redacted | 0 | — | — |

## 6. Contamination meter

`accuracy(zeroinfo_named) − accuracy(zeroinfo_redacted)`, per subject. The two prompts differ by exactly one line (the name), so this is a one-factor measurement of what the model already knows about the named person with no excerpts at all. Given finding 8.1 it is the number that bounds how much of any twin score could be identity rather than evidence.

### standard options

| subject | zeroinfo_named argmax | zeroinfo_redacted argmax | **delta argmax** | delta prob-mass |
|---|---|---|---|---|
| C00792 | 1.000 | 1.000 | **0.000** | 0.000 |
| C01677 | 1.000 | 1.000 | **0.000** | 0.030 |
| C02006 | 1.000 | 1.000 | **0.000** | 0.050 |
| C02013 | 1.000 | 1.000 | **0.000** | -0.010 |
| C02124 | 1.000 | 1.000 | **0.000** | 0.000 |

### stripped options

| subject | zeroinfo_named argmax | zeroinfo_redacted argmax | **delta argmax** | delta prob-mass |
|---|---|---|---|---|
| C00792 | 1.000 | 1.000 | **0.000** | 0.002 |
| C01677 | 1.000 | 1.000 | **0.000** | 0.150 |
| C02006 | 1.000 | 1.000 | **0.000** | 0.083 |
| C02013 | 1.000 | 1.000 | **0.000** | 0.022 |
| C02124 | 1.000 | 1.000 | **0.000** | 0.000 |

## 7. Cost

| subject | model calls | tokens in | tokens out | node-seconds (share) | $ |
|---|---|---|---|---|---|
| C00292 | 167 | 143,565 | 4,757 | 41.3 | 0.00 |
| C00792 | 126 | 172,982 | 13,156 | 114.3 | 0.00 |
| C01677 | 62 | 68,978 | 3,196 | 27.8 | 0.00 |
| C02006 | 48 | 80,841 | 7,831 | 68.0 | 0.00 |
| C02013 | 65 | 137,310 | 11,088 | 96.3 | 0.00 |
| C02124 | 171 | 206,683 | 12,347 | 107.3 | 0.00 |

**Total: 0.1264 node-hours, 639 model calls, 0 API calls, $0.00.** Node-seconds are apportioned by each subject's share of output tokens in the shared job; the jobs shared one engine init.

| job | slurm id | status | projected node-hours | actual node-hours (sacct) |
|---|---|---|---|---|
| stage2_pilot_full | ['50359261'] | completed | 0.1112 | 0.1264 |
| stage2_pilot_smoke | ['50356680', '50358183'] | completed | 0.0653 | 0.228 |

## 8. Findings for bar-lock

Every item here is a PILOT observation or an inherited design limitation. None
of it is a research conclusion, and none of it clears or fails a bar.

### 8.0 THE HEADLINE: the item set is at ceiling, so this pilot measures nothing about twins

**The zero-information baseline scored 100% argmax accuracy on all 17 items.**

A prompt with no excerpts, no programme, no date and no name -- a model that
knows literally nothing about the person -- picked the right answer every single
time, under both option variants. The twin arms also scored 1.00, so:

* **twin - zeroinfo lift is exactly 0.00 in argmax**, because both arms are
  pinned at the ceiling and there is no room above the floor;
* **A4.3's adversarial filter removes ALL 17 items** (its rule is "drop the items
  the zero-information arm got argmax-correct"), leaving **N = 0** in every
  filtered cell. Those tables in section 5 are empty, and that is the filter
  working exactly as designed -- it is telling us the instrument is unusable;
* the only structure left anywhere is in probability mass and in the imposter
  arm, which is the one arm that is NOT at ceiling (0.94 argmax, 0.88 mass).

**This is not a twin result, it is a distractor result.** The forced choice is
solvable by topical coherence alone: the true answer is the guest's real reply to
*this* question, and all three distractors are answers to unrelated questions
from other people's interviews. The model's own reasoning in the completions says
so in as many words -- "Option B directly addresses the host's question about
American responsibility" -- it is matching topic, not modelling a person.

T2 predicted this precisely (finding 8.5): median distractor question-similarity
cosine 0.050, one item of eighteen with a distractor above 0.10. The prediction
was "a model that knows nothing about the person can score above chance". The
measured answer is worse than above chance: it is perfect.

**What this pilot therefore did and did not establish.** It DID establish that
the pipeline works end to end -- draw, split, extraction, distractors, imposter
matching, five-arm rendering, both leakage guards, export, node execution,
ingest, scoring. Every one of those ran clean on real data. It established
NOTHING about twin fidelity, and no number in section 5 should be read as
evidence about one.

**The fix is not in these rules.** It is a materially harder option set. The
levers, in the order I would try them:

1. **Distractors from the SAME subject's other interviews.** Then topic and
   speaker are both controlled and only the specific answer differs. This is the
   single biggest change and it is a D6 amendment.
2. **A much bigger, stratified bank** so the same-bucket, same-length pool has
   enough rows for question similarity to bite (finding 8.5).
3. **A similarity floor as a hard admission rule** -- reject an item whose best
   distractor cannot clear a stated cosine, rather than accepting whatever the
   ladder returns.
4. **Report the zero-information ceiling as a gate**: if the floor arm solves an
   item, that item carries no information about anybody, and it should never
   have entered the set. That is A4.3 applied at BUILD time instead of at score
   time.

All four are bar-lock decisions and none of them is mine.

### 8.1 The redacted arms are name-blind, not identity-blind

SPEC D8 redacts *name variants*. It does not touch affiliations, and the twin
excerpts are full of them. Real lines from the exported `twin_redacted` set:

    "GUEST is chairman of the Department of Sociology a..."          C02013
    "I'm joined now by GUEST, professor of Middle East politics
     at Georgetown U..."                                             C02124
    "GUEST is the author of "Imperium", a novel of anci..."          C02006
    "GUEST, as a former State Department official, can..."           C00792
    "And GUEST, Stanton nuclear security fellow at the Coun..."      C01677

Any model with world knowledge recovers the person from those lines. So
`twin_redacted` is a name-scrubbed arm, not a de-identified one, and the honest
reading of a twin number is "the excerpts help", NOT "the excerpts help without
identity".

This is inherent to D8 as frozen and was accepted as such. It is also exactly
why two controls in the design are load-bearing rather than decorative:

* the **zero-information arms** are the floor every twin number is reported
  against -- the project's standing rule, and on this pilot not a formality;
* the **contamination meter** (`zeroinfo_named - zeroinfo_redacted`, section 6)
  measures what the model already knows about the named person with no excerpts
  at all, which bounds how much of a twin score could be identity rather than
  evidence.

Bar-lock question: does a confirmatory Stage 2 need affiliation redaction, or
does it accept name-only redaction and lean on the meter? Not a pilot decision.

### 8.2 Nickname handling (new rule this pilot, bar-lock item at scale)

The pool's `variants` column carries formal names, so T4's expansion reached
"Matthew"/"Kroenig" but not the "Matt" the excerpts say -- and the guard could
not see it, because the guard and the scrubber share a matcher. A documented
`NICKNAME_SUPPLEMENT` table (standard English hypocorisms only, applied to every
dev subject AND every donor, emitting whole substituted names so T4's frozen
expansion does the matching) now closes it. It caught two leaks:

    C01677  "It's fair to say, Matt GUEST, ..."           twin arms, 1 item
    C01316  "... the blog Syria Comment. Josh, nice ..."  imposter arm, 5 items

The second is the interesting one: Joshua Landis is C00792's *donor*, so his
first name was surviving in the imposter excerpts and had not been spotted.
Zero collateral over-redaction in this corpus slice.

**Bar-lock item:** a hand-maintained table does not scale to 1,153 subjects. The
real answer is a name-normalisation resource, and it is the same decision as the
NER item in 8.6.

### 8.3 D3.2's fuzzy host rule: the 0.60 threshold is PROVISIONAL (T1 round 4)

MediaSum misspells a programme name ("CNN International Diplomatic Linense"),
so D3.2 had to accept a fuzzy descriptor/programme match. The adopted threshold
is **0.60** and it is explicitly provisional pending bar-lock. The evidence it
was set from:

* **Separation**: the true anchor descriptor scores **0.680** against that
  programme string; the best non-anchor descriptor in the same transcripts
  scores **0.379**. A margin of 0.30 -- and a 0.70 threshold would have missed
  the true anchor, which is why the bar is this low.
* **Corpus-wide fire rate** of the adopted predicate: **3.86%** of transcripts
  (1,112 of 28,804), 1,787 turns; the fuzzy arm alone accounts for 202 of them.

It has not been validated against a labelled sample. Review before any
confirmatory-scale use. Its effect here was large and local: C00292's grounding
host turns went 74 -> 330 and its host->guest pairs 18 -> 87, all through one
descriptor at ratio 0.68, with the guest side unchanged.

### 8.4 The imposter donors: register, not topic (T3, and what fixed it)

D7's first implementation measured **how similarly two people talk on air**, not
what they talk about. Plain TF-IDF with raw counts over ~74 documents let
conversational filler dominate the vectors: a British novelist and a US
political strategist scored 0.75, and one generic donor was in the top three for
all six subjects. The v1.2 amendment (drop terms with document frequency > 0.9)
fixed it: six subjects now have six distinct donors, similarities fell to a
meaningful 0.11-0.48, and a novelist gets a novelist.

Three residuals travel with the imposter arm:

* **C00292's donor is a near-miss the rule got wrong.** A UN correspondent was
  matched to a US partisan strategist (Ron Christie, 0.2196), **0.0091** ahead of
  a UN ambassador (Al Hussein, 0.2105) who is the obviously better same-domain
  donor. Not overridden by hand -- the rule is the rule. Cheapest of the six to
  be wrong about, since C00292 is burned for Q-A and its imposter arm never runs.
* **Two margins are near a thousandth of a point**: C02006 -> Walter Mosley by
  **0.0011** and C02013 -> Doris Meissner by **0.0016**. Both winners are the
  more sensible candidate, but neither pair is robust; any further change to turn
  extraction could flip them. That is a consequence of thin grounding text
  (1,397 and 1,714 guest words), not of the matching rule.
* **The control is stronger where the topic has its own vocabulary.** Syria, Arab
  politics and nuclear diplomacy give 0.12-0.13 margins and unambiguous topical
  agreement. "Urban sociology" and "literary fiction" do not exist as distinct
  vocabularies in a corpus of broadcast talk, and those pairs are weaker.

One asymmetry this driver measured: C02013's donor grounding renders at 2,050
words against C02013's own 1,817, so on that subject the imposter arm carries
slightly MORE excerpt text than the twin arm.

### 8.5 The distractors' topic control is weak, and the zero-info arms are how we know

A4 wants three controls on a wrong option: similar length, similar entity
density, similar topic. **Length and density held on every item** -- all 18
matched at relaxation rung 0, the pre-registered control, and the ladder has
never fired. **Topic did not.**

    distractor bank                                652 rows from 167 donors
                                                   (SPEC expected ~2k)
    distractor question-similarity cosine, range   0.016 - 0.102
    median across the 54 distractors               0.050
    items whose best distractor cleared 0.10       1 of 18

A cosine of 0.05 on TF-IDF 1-2 grams means the "most similar" donor question is
about something else entirely: an Egyptian field marshal against Homo sapiens and
LGBT bishops; Kofi Annan against drone strikes.

**Consequence for reading every table in section 5:** the forced choice is easier
than A4 intends, and a model that knows nothing about the person can score above
chance by picking the topically plausible option. The instrument that catches
this is already in the design -- the zero-information arms and the A4.3
adversarial filter -- which is why no twin number in this report appears without
its baseline. The lever for a real topic control is a bigger, stratified bank
(more donors, donors on one-on-one interview programmes), not a change to the
extraction rules.

### 8.6 D5's entity heuristic: three known limitations, all deferred to the NER decision

D5 is a documented pilot-grade heuristic and upgrading it to real NER is a
bar-lock decision. Three limits are pinned by labelled tests so they cannot
change silently:

1. **Spelled-out titles.** D5-r3's abbreviation clause matches all 83 entries of
   the HONORIFIC set, including 58 spelled out in full, so "became president. And
   of course" reads as an abbreviation and glues the next word into a span.
   Measured: 15 of 652 bank rows (2%), 19 occurrences; **4 rows and 0 items would
   change bucket if fixed**, so no option set depends on it.
2. **"St." is not covered.** Not in HONORIFIC, no internal dot, not an initial, so
   "St. Petersburg" still splits and "Petersburg" survives into the stripped text.
3. **A single-token proper noun opening a sentence survives entity-stripping**
   (SPEC v1.7 records this). D5's sentence-initial rule cannot tell it from an
   ordinary capitalised word.

All three degrade the A4.2 entity-stripped option variant only -- they leave a
name in text that variant exists to scrub, which makes the stripped condition a
slightly weaker adversarial re-score than intended. None of them touches the
standard variant. The proposed fix for 1 and 2 is one curated abbreviation
subset instead of all of HONORIFIC; 3 needs NER.

### 8.7 Test-interview Q-A eligibility: a floor proposal

The pilot's binding constraint is not answer length and never was: **23 of the 46
candidate host->guest pairs were dropped for not being questions** (no question
mark, no interrogative or imperative first word), and 0 answers were dropped for
being under 30 words. D4's cue filter is doing the work, and it is doing it
correctly -- those turns are statements and hand-offs.

What actually decides whether a subject can be measured is the shape of its test
interview. Proposal for bar-lock, to be applied at DRAW time rather than
discovered afterwards:

* require the test-interview cluster to yield **>= 3** D4-eligible items, and
* prefer one-on-one interview programmes over roundtables and multi-guest panels.

Evidence from the six: C00292 (a roundtable) yields 0 usable items because every
host turn before one of its guest turns is a statement; C01677 (a three-guest
panel) yields 1, because most host questions are answered by somebody else;
C02124 (a two-person NPR interview, strictly alternating) yields 4 of 6 possible
and is the shape the design wants. A floor of 3 would have rejected two of six
subjects at draw time, at the cost of drawing deeper into the shuffled order.

### 8.8 Items per subject vs H1 power

    C00792  5      C02013  4      C02124  4
    C02006  3      C01677  1      C00292  0 (burned)
    total  17 scoreable items across 5 subjects

Against D4's cap of 20 items PER SUBJECT. The consequences are structural, not
fixable by tuning:

* Any subject-paired contrast has **5 pairs**, and one of those pairs rests on a
  single item, so its per-subject "mean" is one observation.
* This report therefore prints **N per cell** everywhere and runs **no
  significance test at all**. That is deliberate. A p-value on 17 items would
  invite exactly the reading the pilot cannot support.
* For H1 at confirmatory scale the lever is subject selection (8.7), not the
  extraction rules. The pilot's job was to prove the pipeline; it did.

### 8.9 The C00292 burn, and what it is still used for

C00292 (Bassir Pour) was drawn second in the frozen order and is the only subject
retired for Q-A. The story, in order:

1. It first produced **zero** host->guest pairs at all: its CNN transcripts name
   the anchor in full once ("RICHARD ROTH, CNN ANCHOR") and then say "ROTH" for
   the next 35 turns, which the speaker classifier read as a guest.
2. D3.1-r2 (within-transcript surname resolution) and then D3.2 (the programme-
   name anchor rule, 8.3) recovered the anchor: grounding host turns 1 -> 74 ->
   330, host->guest pairs 0 -> 18 -> 87.
3. Its Q-A yield **still did not move off 0**, and no labelling rule can move it:
   DIPLOMATIC LICENSE is a roundtable and every host turn before one of its guest
   turns is a statement, which D4's cue filter correctly rejects.
4. Owner decision: the cue filter stays; C00292 stays a dev subject **forever**
   (burned, never reused, never replaced-and-forgotten); a sixth subject
   (C02124) was added alongside it rather than substituted for it.
5. A later rules change gave it a yield of **1** item with a full option set on
   disk. **The burn does not flip on yield drift.** That one item and its four
   options exist in `subjects/C00292/` and are excluded here by filtering on the
   `burned_for_qa` annotation -- asserted at build, at export, and at verify.

It is a full participant everywhere else, and it is not a passenger: it
contributes **167 of the 469 classifier cases**, more than any other subject.

### 8.10 Classifier prompts are deliberately NOT redacted

SPEC D9 says nothing about redaction, and the follow-up classifier is a
measurement instrument over the corpus rather than an evaluation arm: it reads
three host/guest turns and emits FOLLOW-UP or NEW-TOPIC. Its output is a label on
an interview turn. It feeds descriptive statistics about interview structure --
never a prediction prompt, never an option set, never a score. So a name inside a
classifier prompt cannot leak into anything the twin arms are measured on, and
the prompts carry the transcript text as written ("Mr. Harris, thanks so much for
talking to us").

Recorded as a decision, not an oversight. Redacting them would cost nothing if a
later review prefers uniformity.

### 8.11 Grounding words vs the 2,000-word budget, per subject

T1's standing concern was that four of six subjects had less grounding text than
SPEC D8's `B_pilot` = 2,000 words, so selection would be a no-op. That was
measured on **guest** words. An exchange carries its host turn too, and on the
real segments every subject reaches or nearly reaches the budget:

    subject   segments  exchanges  words available  words rendered
    C00792       2         21          2,177           2,036
    C02013       2         17          2,081           1,817
    C02124       8         68          8,630           2,038
    C01677       2         14          2,425           1,836
    C02006       2         14          1,907           1,937
    C00292      12        177          8,539           (classifier only)

Donor blocks all render at 2,026-2,060 words, so the imposter arm is never
thinner than the twin arm.

Reading: **C02124 is the only subject where most-recent-first selection discards
a lot** (8,630 available against a 2,000 budget). C02013, C01677 and C02006 land
under budget because the skip-and-continue rule declined an oversized exchange,
not because the material ran out. So this pilot still says almost nothing about
selection *policy* -- H2's arms need subjects with several times the budget
available, which is a draw-time criterion, same family as 8.7.

### 8.12 Parse-failure rate per prompt set

`jobs/batch_generate.py` has no re-ask path — it is one vLLM pass per prompt file with no parse hook — so SPEC D9's 'up to 2 re-asks' is unreachable in batch mode and a parse failure is RECORDED, not retried. There are no duplicate `idx` rows anywhere in the export. These are the rates that policy produced.

| prompt set | attempted | parse failures | rate |
|---|---|---|---|
| pred_twin_redacted_standard | 17 | 0 | 0.0000 |
| pred_twin_redacted_stripped | 17 | 0 | 0.0000 |
| pred_twin_named_standard | 17 | 0 | 0.0000 |
| pred_twin_named_stripped | 17 | 1 | 0.0588 |
| pred_zeroinfo_redacted_standard | 17 | 0 | 0.0000 |
| pred_zeroinfo_redacted_stripped | 17 | 0 | 0.0000 |
| pred_zeroinfo_named_standard | 17 | 0 | 0.0000 |
| pred_zeroinfo_named_stripped | 17 | 0 | 0.0000 |
| pred_imposter_redacted_standard | 17 | 0 | 0.0000 |
| pred_imposter_redacted_stripped | 17 | 1 | 0.0588 |
| classify | 469 | 0 | 0.0000 |

## 9. Provenance

| what | value |
|---|---|
| contract | SPEC.md v1.7 (D1-D10) |
| D8 template sha256 | `26def40977f381e732c757bdb16d1c620db415041af59719319cef5434f652b1` |
| D9 rubric sha256 | `053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da` |
| stage2_render.py sha256 | `25a13febf5ee85cf4ef8b4371ecc8162ed0f1685841f518d3399c62151e0425a` |
| followup_render.py sha256 | `37adc0f613343f3734f000eac2ab713d90b6588ba93ad846ef7aca0fcab58fab` |
| model | leonardo-gemma4-31b-it |
| node config | 1 node, 4x A100, tp=4, max-model-len=8192, gpu-mem-util=0.92, temperature=0.0, one engine init per job |
| grounding budget | 2000 words (SPEC D8 B_pilot) |
| exported | 2026-07-26T18:15:22Z |
| driver commit | 4ee33b8 |

### Export manifest digests

| file | prompts | sha256 |
|---|---|---|
| prompts_classify.jsonl | 469 | `c1130293b16ac3f918f5578f99cc6cbee593cecbafd3b3175449bb71658ae673` |
| labels_rule.jsonl | 0 | `6be00a2a7987cabe672b9c91a54a3b56ac883edf601375ac3609065cd90bd63a` |
| prompts_pred_imposter_redacted_standard.jsonl | 17 | `4f070158ed6ddffc660f0d2f5cccb960f71b402fd054d3162c09a5241dea17f6` |
| prompts_pred_imposter_redacted_stripped.jsonl | 17 | `10a6a2783e361c87864277aff6d342a101bc91a9d0e8fce2b1815f5fae89c317` |
| prompts_pred_twin_named_standard.jsonl | 17 | `cc04bf3b8492a811ee2cbb41f21f687acfcb07ad529e93dcc414b843dfd84680` |
| prompts_pred_twin_named_stripped.jsonl | 17 | `3b3144c21ec7b147b5037c1288b4edc23b943e73363eff87a74649380579a57e` |
| prompts_pred_twin_redacted_standard.jsonl | 17 | `3dba704e1ac5f8dee599cdbd83648fdf6d307a7b789455964c2243c949b0986c` |
| prompts_pred_twin_redacted_stripped.jsonl | 17 | `0e1de85720634e9363ef04d3dfd5449fdd8188c2c761a0c65a28e0b2d06ed8a2` |
| prompts_pred_zeroinfo_named_standard.jsonl | 17 | `4d64338b9708c95bc648e99b4e2b069000a7d2185cc38cd0e5131bd1593b1f12` |
| prompts_pred_zeroinfo_named_stripped.jsonl | 17 | `00da9d58416aaf8d4c79d93640bed545d768bcc04af039b2e269c4a10693acf2` |
| prompts_pred_zeroinfo_redacted_standard.jsonl | 17 | `579acad2130b07d24f711432f4d73fc3cebfdc92ead51d1535a856c679a33811` |
| prompts_pred_zeroinfo_redacted_stripped.jsonl | 17 | `6eb2aa4075ee7cd21f92a1c969632c7ea035d3bb1feb896f13081ffdf28cff7f` |
| prompts_smoke.jsonl | 22 | `d9bf22f88bb34a808c92020a11d0f52347dd57ef200a525fad62373a07a250ee` |

Every prompt in this run is reproducible from the committed `exports/` files; `uv run python experiments/stage2_pilot.py verify` re-checks all of the above against the prompts on disk.

