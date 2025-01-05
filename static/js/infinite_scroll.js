let currentPage = 1;
let loading = false;
let hasMore = true;

// Function to save scroll state before leaving
function saveScrollState() {
    const scrollPosition = window.scrollY;
    const posts = Array.from(document.querySelectorAll('.card')).map(card => card.outerHTML);
    const state = {
        scrollPosition,
        posts,
        currentPage,
        hasMore,
        path: window.location.pathname,
        search: window.location.search
    };
    sessionStorage.setItem('scrollState', JSON.stringify(state));
}

// Function to restore scroll state
function restoreScrollState() {
    const savedState = sessionStorage.getItem('scrollState');
    if (savedState) {
        const state = JSON.parse(savedState);
        
        // Redirect if we're on the wrong path
        if (window.location.pathname !== state.path || window.location.search !== state.search) {
            window.location.href = state.path + state.search;
            return;
        }

        const container = document.querySelector('.container');
        
        // Preserve the header elements based on the page
        if (state.path === '/') {
            const sortingButtons = container.querySelector('.d-flex.justify-content-end');
            container.innerHTML = sortingButtons?.outerHTML || '';
        } else if (state.path === '/my_posts') {
            const title = container.querySelector('h2');
            container.innerHTML = '';
            if (title) {
                container.appendChild(title);
            }
        }
        
        // Restore posts
        state.posts.forEach(post => {
            container.insertAdjacentHTML('beforeend', post);
        });
        
        // Restore variables
        currentPage = state.currentPage;
        hasMore = state.hasMore;
        
        // Restore scroll position after a short delay
        setTimeout(() => {
            window.scrollTo(0, state.scrollPosition);
        }, 100);
        
        // Clear saved state
        sessionStorage.removeItem('scrollState');
        
        // Update sort buttons if on index page
        if (state.path === '/') {
            updateSortButtonStates();
        }
    }
}

// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const time = date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        hour12: false 
    });

    if (date.toDateString() === now.toDateString()) {
        return `Posted today at ${time}`;
    }
    else if (date.toDateString() === yesterday.toDateString()) {
        return `Posted yesterday at ${time}`;
    }
    else {
        return `Posted on ${date.toLocaleDateString('en-US', { 
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        })} at ${time}`;
    }
}

// Function to create a post card
function createPostCard(post) {
    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex align-items-center gap-2 mb-1">
                    <small class="text-muted">${formatDate(post.date_created)}</small>
                </div>
                <p class="card-text">
                    <a href="/post/${post.id}" onclick="saveScrollState()">${post.content.length > 350 ? post.content.substring(0, 350) + '...' : post.content}</a>
                </p>

            </div>
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center mb-2" style="border-bottom: solid rgba(128, 128, 128, 0.2);"></div>

             <div class="d-flex justify-content-between align-items-center mb-2 px-3">
                <div>
                    <button onclick="sharePost(${post.id})" class="btn btn-outline-primary btn-sm">
                        📤 Share
                    </button>
                </div>
                <div class="d-flex gap-2">
                    <a href="/post/${post.id}" onclick="saveScrollState()" class="btn btn-outline-primary btn-sm">
                        💌 Comment (${post.comment_count})
                    </a>
                    <a href="/post/${post.id}" onclick="saveScrollState(); likePost(event, ${post.id});" class="btn btn-outline-primary btn-sm">
                        👍 Like (${post.likes})
                    </a>
                </div>
            </div>
        </div>
    `;
}

function sharePost(postId) {
    const postUrl = `${window.location.origin}/post/${postId}`;
    if (navigator.share) {
        navigator.share({
            title: 'AnonCuza | Check out this post!',
            url: postUrl
        }).then(() => {
            console.log('Thanks for sharing!');
        }).catch(console.error);
    } else {
        // Fallback for browsers that do not support the Web Share API
        const tempInput = document.createElement('input');
        document.body.appendChild(tempInput);
        tempInput.value = postUrl;
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        alert('Post URL copied to clipboard!');
    }
}

// Function to show loading indicator
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'text-center my-3';
    loadingDiv.id = 'loading';
    loadingDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    document.querySelector('.container').appendChild(loadingDiv);
}

// Function to remove loading indicator
function hideLoading() {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Function to update sort button states
function updateSortButtonStates() {
    const urlParams = new URLSearchParams(window.location.search);
    const currentSort = urlParams.get('sort_by');
    const sortButtons = document.querySelectorAll('a[href*="sort_by"]');
    
    sortButtons.forEach(button => {
        const buttonUrl = new URL(button.href);
        const buttonSort = buttonUrl.searchParams.get('sort_by');
        
        if ((buttonSort === currentSort) || (buttonSort === 'newest' && !currentSort)) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

// Function to load more posts
async function loadMorePosts() {
    if (loading || !hasMore) return;
    
    loading = true;
    showLoading();
    const postsContainer = document.querySelector('.container');
    const isMyPosts = window.location.pathname === '/my_posts';
    const endpoint = isMyPosts ? '/api/my_posts' : '/api/posts';
    
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const sortBy = urlParams.get('sort_by') || 'newest';
        
        const response = await fetch(`${endpoint}?page=${currentPage}&sort_by=${sortBy}`);
        const posts = await response.json();
        
        if (posts.length === 0) {
            hasMore = false;
            hideLoading();
            if (currentPage === 1) {
                postsContainer.innerHTML += '<p class="text-center mt-4">No posts yet!</p>';
            }
            return;
        }
        
        posts.forEach(post => {
            postsContainer.insertAdjacentHTML('beforeend', createPostCard(post));
        });
        
        currentPage++;
    } catch (error) {
        console.error('Error loading posts:', error);
        postsContainer.innerHTML += '<p class="text-center text-danger">Error loading posts. Please try again.</p>';
    } finally {
        loading = false;
        hideLoading();
    }
}

// Infinite scroll handler
function handleScroll() {
    const scrollPosition = window.innerHeight + window.scrollY;
    const pageHeight = document.documentElement.scrollHeight;
    
    if (scrollPosition >= pageHeight - 1000) {
        loadMorePosts();
    }
}

// Initialize infinite scroll if on index or my_posts page
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    if (path === '/' || path === '/my_posts') {
        const container = document.querySelector('.container');
        
        // Check if we're returning from a post
        if (sessionStorage.getItem('scrollState')) {
            restoreScrollState();
        } else {
            if (path === '/') {
                const sortingButtons = container.querySelector('.d-flex.justify-content-end');
                if (sortingButtons) {
                    const newContent = sortingButtons.outerHTML;
                    container.innerHTML = newContent;
                }
                updateSortButtonStates();
            } else {
                const title = container.querySelector('h2');
                container.innerHTML = '';
                if (title) {
                    container.appendChild(title);
                }
            }
            
            loadMorePosts();
        }
        
        window.addEventListener('scroll', handleScroll);

        if (path === '/') {
            // Add click handlers for sort buttons
            document.addEventListener('click', (e) => {
                const sortLink = e.target.closest('a[href*="sort_by"]');
                if (sortLink) {
                    e.preventDefault();
                    const url = new URL(sortLink.href);
                    const newSortBy = url.searchParams.get('sort_by');
                    
                    window.history.pushState({}, '', `/?sort_by=${newSortBy}`);
                    
                    currentPage = 1;
                    hasMore = true;
                    const sortingButtons = container.querySelector('.d-flex.justify-content-end');
                    container.innerHTML = sortingButtons.outerHTML;
                    updateSortButtonStates();
                    loadMorePosts();
                }
            });
        }
    }
});