"""대표 프로젝트 지정과 한 줄 성과를 한 번만 심어 둡니다.

이 값들은 UX 개편에서 새로 생긴 필드(`is_featured`, `key_result`)라
기존 DB 에는 비어 있습니다. 비워 두면 첫 화면의 '대표 프로젝트' 섹션이
통째로 렌더링되지 않으므로, 배포 시점에 한 번 채웁니다.

`key_result` 는 전부 해당 프로젝트의 description / outcome / content 에
이미 있던 문장을 줄인 것입니다. 새로운 사실을 만들지 않았습니다.
한 번 실행되고 끝나므로, 이후에는 관리자 페이지에서 자유롭게 바꾸면 됩니다.

pk 로 찾되 제목 일부가 맞는지 확인하고, 어긋나면 건드리지 않습니다.
"""

from django.db import migrations

# pk: (제목 확인용 조각, is_featured, order, key_result)
SEED = {
    14: ("SNU AI Challenge", True, 40, "Kaggle Exact Match 0.513 · 8GB GPU로 3B VLM 파인튜닝"),
    12: ("픽합주", True, 39, "서울 25개 구 합주실 데이터 통합"),
    10: ("리뷰 감성 분석", True, 38, "모호한 3점 리뷰 89% 재분류"),
    11: ("개인 포트폴리오 사이트", True, 37, "기획부터 배포까지 48시간"),
    13: ("보안 취약점", False, None, "우수상"),
    9: ("풍력 발전량", False, None, "2TB 규모 데이터 전처리·병합"),
    7: ("SAS KOREA", False, None, "소모임 4개 팀 구성·운영"),
    6: ("제스처", False, None, "웹캠 기반 실시간 제스처 인식"),
    5: ("데이터톤", False, None, "XGBoost + KoBERT 하이브리드 파이프라인"),
    4: ("전통시장", False, None, "유동인구 기여도 부재 규명"),
    3: ("뉴스 링커", False, None, "크롬 확장 + Flask 서버 연동"),
    2: ("빨뚜", False, None, "웹·서버·IoT 하드웨어 연동 완성"),
    # id 8, id 1 은 outcome 이 '결과'가 아니라 과제/역량 서술이라 비워 둔다.
}


def seed(apps, schema_editor):
    Project = apps.get_model("portfolio", "Project")

    for pk, (title_fragment, featured, order, key_result) in SEED.items():
        project = Project.objects.filter(pk=pk).first()
        if project is None or title_fragment not in project.title:
            # 다른 환경이라 pk 가 어긋난 경우 — 잘못된 프로젝트를 건드리지 않는다.
            continue

        project.key_result = key_result
        project.is_featured = featured
        if order is not None:
            project.order = order
        project.save(update_fields=["key_result", "is_featured", "order"])


def unseed(apps, schema_editor):
    """되돌리기: 심었던 값만 비웁니다. order 는 원복하지 않습니다."""
    Project = apps.get_model("portfolio", "Project")
    Project.objects.filter(pk__in=SEED).update(key_result="", is_featured=False)


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0024_profile_headline_profile_resume_url_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
