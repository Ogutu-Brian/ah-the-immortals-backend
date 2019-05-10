from rest_framework.exceptions import APIException
from rest_framework.generics import ListCreateAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .exceptions import ArticleNotFound
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from .models import Article, Tag
from .serializers import (
    ArticleSerializer,
    add_tag_list,
    ArticlePaginator
)


class ListCreateArticleAPIView(ListCreateAPIView):
    """
    Create Article
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = ArticleSerializer

    def create(self, request):
        """
        Create an article
        """
        tag_names = request.data.get("tags")
        article = request.data
        article["author"] = request.user.pk
        serializer = self.serializer_class(
            data=article,
            remove_fields=['like', 'created_at', 'updated_at',
                           'dislike', 'likesCount', 'dislikesCount'])
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=request.user)
        data = serializer.data
        if tag_names:
            add_tag_list(tag_names, article)
        data["tagList"] = article.tagList
        return Response(
            data=data,
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        """
        Get all articles
        """
        page_limit = request.GET.get('page_limit')
        if not page_limit:
            page_limit = 10
        else:
            invalid_response = Response(
                data={
                    "detail": "Invalid page limit"
                },
                status=status.HTTP_404_NOT_FOUND
            )
            if not page_limit.isdigit():
                return invalid_response
            elif int(page_limit) < 1:
                return invalid_response
        articles = Article.objects.all()
        paginator = ArticlePaginator()
        paginator.page_size = page_limit
        result = paginator.paginate_queryset(articles, request)
        serializer = ArticleSerializer(result, many=True,
                                       remove_fields=['like',
                                                      'dislike',
                                                      'likesCount',
                                                      'dislikesCount'])
        response = paginator.get_paginated_response({
            "articles": serializer.data
        })
        return response


class RetrieveUpdateArticleAPIView(GenericAPIView):
    """
    Retrive, Update and Delete an article
    """
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = ArticleSerializer

    def retrieve_article(self, slug):
        """
        Fetch one article
        """
        try:
            article = Article.objects.get(slug=slug)
            return article
        except Article.DoesNotExist:
            raise ArticleNotFound

    def get(self, request, slug):
        """
        Get one article
        """
        article = self.retrieve_article(slug)
        if article:
            serializer = ArticleSerializer(
                article,
                context={'article': slug, 'request': request},
                many=False
            )
            return Response(
                {"article": serializer.data},
                status=status.HTTP_200_OK
            )

    def patch(self, request, slug):
        """
        Update an article
        """
        article = self.retrieve_article(slug)
        user = request.user
        if article.author == user:
            serializer = ArticleSerializer(
                instance=article,
                data=request.data,
                partial=True,
                remove_fields=['like', 'created_at', 'updated_at',
                               'dislike', 'likesCount', 'dislikesCount']
            )
            serializer.is_valid(raise_exception=True)
            article = serializer.save()
            data = serializer.data
            tag_names = request.data.get("tags")
            if tag_names:
                article.clear_tags()
                add_tag_list(tag_names, article)
            data["tagList"] = article.tagList
            return Response(
                data={
                    "article": data
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                data={
                    "errors": {
                        "error": [
                            "Cannot edit an article that is not yours"
                        ]
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )

    def delete(self, request, slug):
        """
        Delete an article
        """
        article = self.retrieve_article(slug)
        user = request.user
        if article.author == user:
            article.clear_tags()
            article.delete()
        else:
            return Response({"errors": {
                "error": [
                    "Cannot delete an article that is not yours"
                ]}},
                status.HTTP_403_FORBIDDEN)
        return Response({"message": "Article deleted"},
                        status.HTTP_200_OK)


class FetchTags(GenericAPIView):
    """
    Fetchs all tags from database
    """

    def get(self, request):
        """
        Gets all articles
        """
        tags = Tag.objects.all()
        if not tags:
            response = Response(
                data={
                    "errors": {
                        "tags":
                        ["There are no tags in Authors Heaven at the moment"]
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            response = Response(
                data={
                    "tags": [tag.tag_name for tag in tags]
                },
                status=status.HTTP_200_OK
            )
        return response


class LikeDislikeView(GenericAPIView):
    """
    A generic class to like and dislike articles
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ArticleSerializer

    def post(self, request, slug, vote_type):
        """
        A method to post a likes
        """
        article_inst = RetrieveUpdateArticleAPIView()
        article = article_inst.retrieve_article(slug)

        vote_type_list = ["like", "dislike"]
        if vote_type not in vote_type_list:
            return Response({
                'errors': {
                    'vote_verb': ['Vote verb specified does not exist']
                }
            }, status=status.HTTP_404_NOT_FOUND)

        def get_vot_response(votetype):
            if vote_type == "dislike":
                article.votes.down(request.user.id)
                return_string = "Dislike posted successfully"
            else:
                article.votes.up(request.user.id)
                return_string = "Like posted successfully"
            return return_string
        serializer = ArticleSerializer(
            article,
            context={'article': slug, 'request': request, },
            many=False)
        vote_resp = get_vot_response(vote_type)
        response = Response({
            "article": serializer.data,
            "message": vote_resp
        }, status=status.HTTP_200_OK)

        return response

    def delete(self, request, slug, vote_type):
        """
        A method to delete a vote for a certain article
        """
        article = RetrieveUpdateArticleAPIView().retrieve_article(slug)
        if article.votes.delete(request.user.id):
            return Response({
                "message": ["Vote delete successfully"]
            }, status=status.HTTP_200_OK)
        return Response({
            'errors': {
                'error': 'You have not liked/disliked this article'
            }
        }, status=status.HTTP_404_NOT_FOUND)