from scripts.editorial_topic_scope import topic_fits, stock_query, teacher_intent

def test_unrelated_military_trends_do_not_become_korean_hiring_articles():
    assert not topic_fits('https://jobkoreaglobal.com','Marine Corps recruitment')
    assert not topic_fits('https://jobkoreaglobal.com','National Guard Korea')
    assert topic_fits('https://jobkoreaglobal.com','Korea foreign hire document handover')

def test_photos_describe_a_scene_instead_of_matching_every_seo_word():
    assert stock_query('teacher recruitment and sponsorship fit in Korea','Recruitment')=='classroom teacher'
    assert stock_query('Korea international talent acquisition','Recruitment')=='job interview'
    assert stock_query('unknown named event','News')=='unknown named event'

def test_reworded_teacher_recruitment_is_same_intent_but_induction_is_distinct():
    a=teacher_intent('How employers should structure teacher recruitment and visa sponsorship in Korea')
    b=teacher_intent('Employer steps to compliant teacher recruitment and sponsorship fit in Korea')
    assert a==b and a is not None
    assert teacher_intent('A new teacher’s first week: handovers and classroom access')!=a
