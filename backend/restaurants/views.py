from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .services.hotpepper_client import (
    search_restaurants,
    search_by_keyword,
    get_budget_master,
    get_genre_master,
)
from .models import (
    UserProfile,
    Shop,
    Favorite,
    VisitRecord,
    Rating,
    Comment,
    SearchHistory,
)
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    FavoriteSerializer,
    VisitRecordSerializer,
    RatingSerializer,
    CommentSerializer,
    CommentReadSerializer,
    SearchHistorySerializer,
    ShopSerializer,
)
import logging

logger = logging.getLogger(__name__)


@api_view(["GET"])
def ping(request):
    return Response({"ok": True, "message": "API is working"})


@api_view(["GET"])
def search(request):
    """
    店舗検索
    GET /api/restaurants/search
    Supports both GPS (lat/lng) mode and keyword (station name) mode.
    """
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    range_val = request.GET.get("range", 3)
    budget = request.GET.get("budget")
    genre = request.GET.get("genre")
    keyword = request.GET.get("keyword")
    people = request.GET.get("people")
    free_drink = request.GET.get("free_drink")
    free_food = request.GET.get("free_food")

    # Station mode: keyword is provided but no lat/lng
    if not lat or not lng:
        if not keyword:
            return Response(
                {"error": "Either lat/lng or keyword is required."}, status=400
            )
        try:
            range_val = int(range_val)
            if people:
                people = int(people)
        except ValueError:
            return Response({"error": "Invalid numerical parameters."}, status=400)
        try:
            shops = search_by_keyword(
                keyword=keyword,
                range=range_val,
                budget=budget,
                genre=genre,
                people=people,
                free_drink=free_drink,
                free_food=free_food,
            )
            # 検索履歴保存 (ログイン済みユーザーのみ)
            if request.user.is_authenticated:
                SearchHistory.objects.create(
                    user=request.user,
                    query_params={
                        "mode": "keyword",
                        "keyword": keyword,
                        "range": range_val,
                        "budget": budget,
                        "genre": genre,
                        "people": people,
                        "free_drink": free_drink,
                        "free_food": free_food,
                    },
                    result_count=len(shops),
                )
            return Response({"shops": shops})
        except Exception as e:
            logger.error(f"Search API Error (keyword mode): {e}")
            return Response(
                {"error": "Internal server error during search."}, status=500
            )

    # GPS mode
    try:
        lat = float(lat)
        lng = float(lng)
        range_val = int(range_val)
        if people:
            people = int(people)
    except ValueError:
        return Response({"error": "Invalid numerical parameters."}, status=400)

    try:
        shops = search_restaurants(
            lat=lat,
            lng=lng,
            range=range_val,
            budget=budget,
            genre=genre,
            keyword=keyword,
            people=people,
            free_drink=free_drink,
            free_food=free_food,
        )
        # 検索履歴保存 (ログイン済みユーザーのみ)
        if request.user.is_authenticated:
            SearchHistory.objects.create(
                user=request.user,
                query_params={
                    "mode": "gps",
                    "lat": lat,
                    "lng": lng,
                    "range": range_val,
                    "budget": budget,
                    "genre": genre,
                    "keyword": keyword,
                    "people": people,
                    "free_drink": free_drink,
                    "free_food": free_food,
                },
                result_count=len(shops),
            )
        return Response({"shops": shops})
    except Exception as e:
        logger.error(f"Search API Error: {e}")
        return Response({"error": "Internal server error during search."}, status=500)


@api_view(["GET"])
def budgets(request):
    """
    予算マスタ取得
    GET /api/restaurants/budgets
    """
    try:
        data = get_budget_master()
        return Response({"results": data})
    except Exception as e:
        logger.error(f"Budget API Error: {e}")
        return Response({"error": "Could not fetch budgets"}, status=500)


@api_view(["GET"])
def genres(request):
    """
    ジャンルマスタ取得
    GET /api/restaurants/genres
    """
    try:
        data = get_genre_master()
        return Response({"results": data})
    except Exception as e:
        logger.error(f"Genre API Error: {e}")
        return Response({"error": "Could not fetch genres"}, status=500)


# ============================================================
# Auth Endpoints
# ============================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """ユーザー登録"""
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    email = ser.validated_data["email"]
    password = ser.validated_data["password"]
    display_name = ser.validated_data.get("display_name", "")

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "このメールアドレスは既に登録されています"}, status=400
        )

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
    )
    UserProfile.objects.create(
        user=user, display_name=display_name or email.split("@")[0]
    )
    login(request, user)
    return Response(UserSerializer(user).data, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """ログイン"""
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    email = ser.validated_data["email"]
    password = ser.validated_data["password"]

    user = authenticate(request, username=email, password=password)
    if not user:
        return Response(
            {"error": "メールアドレスまたはパスワードが正しくありません"}, status=401
        )

    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
def logout_view(request):
    """ログアウト"""
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """現在のユーザー情報"""
    return Response(UserSerializer(request.user).data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """プロフィール更新"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    display_name = request.data.get("display_name")
    favorite_genre = request.data.get("favorite_genre")
    theme = request.data.get("theme")

    if display_name is not None:
        profile.display_name = display_name
    if favorite_genre is not None:
        profile.favorite_genre = favorite_genre
    if theme is not None:
        profile.theme = theme
    profile.save()
    return Response(UserSerializer(request.user).data)


# ============================================================
# Shop Upsert (create or get from HP API data)
# ============================================================
def get_or_create_shop(shop_data):
    """HotPepper APIのデータから Shop を作成/取得"""
    shop_id = shop_data.get("id", "")
    if not shop_id:
        return None
    shop, _ = Shop.objects.update_or_create(
        hotpepper_id=shop_id,
        defaults={
            "name": shop_data.get("name", ""),
            "photo_url": shop_data.get("photo", ""),
            "genre": shop_data.get("genre", ""),
            "budget": shop_data.get("budget", ""),
            "address": shop_data.get("address", ""),
            "lat": shop_data.get("lat"),
            "lng": shop_data.get("lng"),
            "url": shop_data.get("url", ""),
            "open_hours": shop_data.get("open", ""),
        },
    )
    return shop


# ============================================================
# Favorites API
# ============================================================
@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def favorites_view(request):
    if request.method == "GET":
        favs = Favorite.objects.filter(user=request.user).select_related("shop")
        return Response(FavoriteSerializer(favs, many=True).data)

    elif request.method == "POST":
        shop_data = request.data.get("shop", {})
        shop = get_or_create_shop(shop_data)
        if not shop:
            return Response({"error": "Invalid shop data"}, status=400)
        fav, created = Favorite.objects.get_or_create(user=request.user, shop=shop)
        if not created:
            return Response({"message": "Already favorited"}, status=200)
        return Response(FavoriteSerializer(fav).data, status=201)

    elif request.method == "DELETE":
        shop_id = request.data.get("shop_id", "")
        try:
            shop = Shop.objects.get(hotpepper_id=shop_id)
            Favorite.objects.filter(user=request.user, shop=shop).delete()
        except Shop.DoesNotExist:
            pass
        return Response({"ok": True})


# ============================================================
# Visit Count API
# ============================================================
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def visits_view(request):
    if request.method == "GET":
        records = VisitRecord.objects.filter(
            user=request.user, visit_count__gt=0
        ).select_related("shop")
        return Response(VisitRecordSerializer(records, many=True).data)

    elif request.method == "POST":
        shop_data = request.data.get("shop", {})
        visit_count = request.data.get("visit_count", 0)
        shop = get_or_create_shop(shop_data)
        if not shop:
            return Response({"error": "Invalid shop data"}, status=400)
        record, _ = VisitRecord.objects.update_or_create(
            user=request.user, shop=shop, defaults={"visit_count": visit_count}
        )
        return Response(VisitRecordSerializer(record).data)


# ============================================================
# Rating API
# ============================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ratings_view(request):
    shop_data = request.data.get("shop", {})
    score = request.data.get("score", 0)
    shop = get_or_create_shop(shop_data)
    if not shop:
        return Response({"error": "Invalid shop data"}, status=400)
    rating, _ = Rating.objects.update_or_create(
        user=request.user, shop=shop, defaults={"score": float(score)}
    )
    return Response(RatingSerializer(rating).data)


# ============================================================
# Comments API (shared across all users)
# ============================================================
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def comments_view(request, shop_id):
    """GET: 特定店舗の全コメント, POST: コメント投稿"""
    try:
        shop = Shop.objects.get(hotpepper_id=shop_id)
    except Shop.DoesNotExist:
        if request.method == "GET":
            return Response([])
        return Response({"error": "Shop not found"}, status=404)

    if request.method == "GET":
        comments = Comment.objects.filter(shop=shop)
        return Response(CommentReadSerializer(comments, many=True).data)

    elif request.method == "POST":
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Comment text is required"}, status=400)

        user = request.user if request.user.is_authenticated else None
        author_name = "匿名"
        if user:
            profile = getattr(user, "profile", None)
            author_name = profile.display_name if profile else user.username

        comment = Comment.objects.create(
            shop=shop,
            user=user,
            author_name=author_name,
            text=text,
        )
        return Response(CommentReadSerializer(comment).data, status=201)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def comment_detail_view(request, comment_id):
    """PUT: 自分のコメント編集, DELETE: 自分のコメント削除"""
    try:
        comment = Comment.objects.get(id=comment_id, user=request.user)
    except Comment.DoesNotExist:
        return Response({"error": "Comment not found or not yours"}, status=404)

    if request.method == "PUT":
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Comment text is required"}, status=400)
        comment.text = text
        comment.save()
        return Response(CommentReadSerializer(comment).data)

    elif request.method == "DELETE":
        comment.delete()
        return Response({"ok": True})


# ============================================================
# Search History API
# ============================================================
@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def search_history_view(request):
    if request.method == "GET":
        histories = SearchHistory.objects.filter(user=request.user)[:50]  # 最新50件
        return Response(SearchHistorySerializer(histories, many=True).data)

    elif request.method == "POST":
        query_params = request.data.get("query_params", {})
        result_count = request.data.get("result_count", 0)
        SearchHistory.objects.create(
            user=request.user, query_params=query_params, result_count=result_count
        )
        return Response({"ok": True}, status=201)

    elif request.method == "DELETE":
        SearchHistory.objects.filter(user=request.user).delete()
        return Response({"ok": True})


# ============================================================
# Share API
# ============================================================
@api_view(["GET"])
def share_view(request, shop_id):
    """店舗のシェア用URL生成"""
    shop = None
    try:
        shop = Shop.objects.get(hotpepper_id=shop_id)
    except Shop.DoesNotExist:
        # DBにない場合も共有可能にする
        logger.info(f"Share requested for unknown shop {shop_id}")

    # アプリ内の店舗詳細ページURL
    share_url = f"{request.build_absolute_uri('/')}#/detail?shop_id={shop_id}"

    # シェア用テキスト
    shop_name = shop.name if shop else ""
    share_text = f"おすすめの居酒屋{('「' + shop_name + '」') if shop_name else ''}を見つけました！\n{share_url}"

    response_data = {
        "shop": ShopSerializer(shop).data if shop else None,
        "share_url": share_url,
        "share_text": share_text,
        "encoded_text": share_text.replace("\n", "%0A"),  # URLエンコード用
    }
    return Response(response_data)
