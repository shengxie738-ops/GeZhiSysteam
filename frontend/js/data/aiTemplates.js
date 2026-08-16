export const problemReviews = {
    // === 大类 1：数组与链表 ===
    two_sum: {
        complexity: `- **时间复杂度**：$O(N)$，利用哈希表（Map）一次遍历即可找到配对，比 $O(N^2)$ 的双重循环暴力法更为高效。\n- **空间复杂度**：$O(N)$，最坏情况下需要将数组中的所有元素都存入 Map。`,
        code: `function twoSum(nums, target) {\n    const map = new Map();\n    for (let i = 0; i < nums.length; i++) {\n        const complement = target - nums[i];\n        if (map.has(complement)) {\n            return [map.get(complement), i];\n        }\n        map.set(nums[i], i);\n    }\n    return [];\n}`
    },
    reverse_list: {
        complexity: `- **时间复杂度**：$O(N)$，其中 N 是链表的长度，只需单次遍历。\n- **空间复杂度**：$O(1)$，迭代法只需要修改指针指向，仅需常数级别辅助空间。`,
        code: `function reverseList(head) {\n    let prev = null;\n    let curr = head;\n    while (curr) {\n        let nextTemp = curr.next;\n        curr.next = prev;\n        prev = curr;\n        curr = nextTemp;\n    }\n    return prev;\n}`
    },
    merge_two_lists: {
        complexity: `- **时间复杂度**：$O(M+N)$，其中 M 和 N 分别为两个链表的节点个数。\n- **空间复杂度**：$O(1)$，通过构造虚拟头节点进行原地指针拼接，时空效率极高。`,
        code: `function mergeTwoLists(l1, l2) {\n    let dummy = { val: -1, next: null };\n    let curr = dummy;\n    while (l1 && l2) {\n        if (l1.val <= l2.val) {\n            curr.next = l1;\n            l1 = l1.next;\n        } else {\n            curr.next = l2;\n            l2 = l2.next;\n        }\n        curr = curr.next;\n    }\n    curr.next = l1 || l2;\n    return dummy.next;\n}`
    },
    has_cycle: {
        complexity: `- **时间复杂度**：$O(N)$，当链表无环时，快指针直接到底；有环时快慢指针必定在环内相遇。\n- **空间复杂度**：$O(1)$，仅需快慢两个指针做原地追踪，优于使用哈希表保存结点的 $O(N)$ 空间解法。`,
        code: `function hasCycle(head) {\n    if (!head || !head.next) return false;\n    let slow = head;\n    let fast = head.next;\n    while (slow !== fast) {\n        if (!fast || !fast.next) return false;\n        slow = slow.next;\n        fast = fast.next.next;\n    }\n    return true;\n}`
    },
    remove_nth_from_end: {
        complexity: `- **时间复杂度**：$O(N)$，使用双指针（快慢指针）间隔 N 个身位，仅需一次扫描。\n- **空间复杂度**：$O(1)$，原地删除。`,
        code: `function removeNthFromEnd(head, n) {\n    let dummy = { val: 0, next: head };\n    let first = dummy;\n    let second = dummy;\n    for (let i = 0; i <= n; i++) {\n        first = first.next;\n    }\n    while (first) {\n        first = first.next;\n        second = second.next;\n    }\n    second.next = second.next.next;\n    return dummy.next;\n}`
    },

    // === 大类 2：栈与队列 ===
    valid_parentheses: {
        complexity: `- **时间复杂度**：$O(N)$，只需遍历一次字符串。\n- **空间复杂度**：$O(N)$，最坏情况下所有括号都是左括号，需全部入栈。`,
        code: `function isValid(s) {\n    const stack = [];\n    const map = { ')': '(', '}': '{', ']': '[' };\n    for (let char of s) {\n        if (char in map) {\n            if (stack.length === 0 || stack[stack.length - 1] !== map[char]) {\n                return false;\n            }\n            stack.pop();\n        } else {\n            stack.push(char);\n        }\n    }\n    return stack.length === 0;\n}`
    },
    min_stack: {
        complexity: `- **时间复杂度**：所有方法（push, pop, top, getMin）均为 $O(1)$，满足题目常数时间检索要求。\n- **空间复杂度**：$O(N)$，辅助最小栈用于记录随主栈水位起伏的局部最小值。`,
        code: `function testMinStack(commands, values) {\n    class MinStack {\n        constructor() { this.stack = []; this.minStack = []; }\n        push(x) {\n            this.stack.push(x);\n            if (this.minStack.length === 0 || x <= this.minStack[this.minStack.length-1]) {\n                this.minStack.push(x);\n            }\n        }\n        pop() {\n            const val = this.stack.pop();\n            if (val === this.minStack[this.minStack.length-1]) {\n                this.minStack.pop();\n            }\n        }\n        top() { return this.stack[this.stack.length-1]; }\n        getMin() { return this.minStack[this.minStack.length-1]; }\n    }\n    \n    const stack = new MinStack();\n    const out = [];\n    commands.forEach((cmd, i) => {\n        if (cmd === 'push') stack.push(values[i]);\n        else if (cmd === 'pop') stack.pop();\n        else if (cmd === 'top') out.push(stack.top());\n        else if (cmd === 'getMin') out.push(stack.getMin());\n    });\n    return out;\n}`
    },
    queue_by_stacks: {
        complexity: `- **时间复杂度**：push为 $O(1)$；pop/peek操作在最坏情况下需要转移元素，但摊还时间复杂度（Amortized Time Complexity）为 $O(1)$。\n- **空间复杂度**：$O(N)$，用于存储队列中的元素。`,
        code: `function testMyQueue(commands, values) {\n    class MyQueue {\n        constructor() { this.stackIn = []; this.stackOut = []; }\n        push(x) { this.stackIn.push(x); }\n        pop() {\n            this.move();\n            return this.stackOut.pop();\n        }\n        peek() {\n            this.move();\n            return this.stackOut[this.stackOut.length-1];\n        }\n        empty() {\n            return this.stackIn.length === 0 && this.stackOut.length === 0;\n        }\n        move() {\n            if (this.stackOut.length === 0) {\n                while (this.stackIn.length > 0) {\n                    this.stackOut.push(this.stackIn.pop());\n                }\n            }\n        }\n    }\n    const queue = new MyQueue();\n    const out = [];\n    commands.forEach((cmd, i) => {\n        if (cmd === 'push') queue.push(values[i]);\n        else if (cmd === 'pop') out.push(queue.pop());\n        else if (cmd === 'peek') out.push(queue.peek());\n        else if (cmd === 'empty') out.push(queue.empty());\n    });\n    return out;\n}`
    },
    eval_rpn: {
        complexity: `- **时间复杂度**：$O(N)$，扫描逆波兰算术表达式数组一次。\n- **空间复杂度**：$O(N)$，栈中最多存储 $N/2$ 个操作数。`,
        code: `function evalRPN(tokens) {\n    const stack = [];\n    for (let t of tokens) {\n        if (['+', '-', '*', '/'].includes(t)) {\n            const b = stack.pop();\n            const a = stack.pop();\n            if (t === '+') stack.push(a + b);\n            else if (t === '-') stack.push(a - b);\n            else if (t === '*') stack.push(a * b);\n            else {\n                const val = a / b;\n                stack.push(val > 0 ? Math.floor(val) : Math.ceil(val));\n            }\n        } else {\n            stack.push(Number(t));\n        }\n    }\n    return stack.pop();\n}`
    },
    sliding_window_max: {
        complexity: `- **时间复杂度**：$O(N)$，利用单调队列维护窗口最大值，每个元素最多入队出队一次。\n- **空间复杂度**：$O(k)$，双端队列最多维护窗口大小 $k$ 的索引。`,
        code: `function maxSlidingWindow(nums, k) {\n    const q = [];\n    const res = [];\n    for (let i = 0; i < nums.length; i++) {\n        while (q.length > 0 && nums[q[q.length - 1]] <= nums[i]) {\n            q.pop();\n        }\n        q.push(i);\n        if (q[0] <= i - k) {\n            q.shift();\n        }\n        if (i >= k - 1) {\n            res.push(nums[q[0]]);\n        }\n    }\n    return res;\n}`
    },

    // === 大类 3：树与二叉树 ===
    tree_max_depth: {
        complexity: `- **时间复杂度**：$O(N)$，二叉树每个节点只会被递归遍历一次。\n- **空间复杂度**：$O(H)$，H 为树的高度。最坏情况下树呈链状（$O(N)$），最好情况下呈满二叉树（$O(\log N)$）。`,
        code: `function maxDepth(root) {\n    if (!root) return 0;\n    return Math.max(maxDepth(root.left), maxDepth(root.right)) + 1;\n}`
    },
    invert_tree: {
        complexity: `- **时间复杂度**：$O(N)$，翻转操作需要访问并调换树中每个结点的左右子指针。\n- **空间复杂度**：$O(H)$，取决于递归系统调用栈的深度。`,
        code: `function invertTree(root) {\n    if (!root) return null;\n    const left = invertTree(root.left);\n    const right = invertTree(root.right);\n    root.left = right;\n    root.right = left;\n    return root;\n}`
    },
    preorder_traversal: {
        complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(H)$，递归栈的深度。`,
        code: `function preorderTraversal(root) {\n    const res = [];\n    function dfs(node) {\n        if (!node) return;\n        res.push(node.val);\n        dfs(node.left);\n        dfs(node.right);\n    }\n    dfs(root);\n    return res;\n}`
    },
    inorder_traversal: {
        complexity: `- **时间复杂度**：$O(N)$，每个节点遍历一次。\n- **空间复杂度**：$O(H)$。`,
        code: `function inorderTraversal(root) {\n    const res = [];\n    function dfs(node) {\n        if (!node) return;\n        dfs(node.left);\n        res.push(node.val);\n        dfs(node.right);\n    }\n    dfs(root);\n    return res;\n}`
    },
    level_order: {
        complexity: `- **时间复杂度**：$O(N)$，每个节点被放入队列一次并取出一遍。\n- **空间复杂度**：$O(N)$，最底层的叶子节点最多占 $O(N)$ 级别的队列存储。`,
        code: `function levelOrder(root) {\n    if (!root) return [];\n    const res = [];\n    const queue = [root];\n    while (queue.length > 0) {\n        const levelSize = queue.length;\n        const currentLevel = [];\n        for (let i = 0; i < levelSize; i++) {\n            const node = queue.shift();\n            currentLevel.push(node.val);\n            if (node.left) queue.push(node.left);\n            if (node.right) queue.push(node.right);\n        }\n        res.push(currentLevel);\n    }\n    return res;\n}`
    },

    // === 大类 4：排序与搜索 ===
    bubble_sort: {
        complexity: `- **时间复杂度**：$O(N^2)$。当数组已经有序时，通过 swapped 标志位剪枝优化，可以达到 $O(N)$ 的最佳时间复杂度。\n- **空间复杂度**：$O(1)$，属于典型的原地（In-place）排序算法。`,
        code: `function bubbleSort(arr) {\n    const len = arr.length;\n    let swapped;\n    for (let i = 0; i < len - 1; i++) {\n        swapped = false;\n        for (let j = 0; j < len - 1 - i; j++) {\n            if (arr[j] > arr[j + 1]) {\n                const temp = arr[j];\n                arr[j] = arr[j + 1];\n                arr[j + 1] = temp;\n                swapped = true;\n            }\n        }\n        if (!swapped) break;\n    }\n    return arr;\n}`
    },
    quick_sort: {
        complexity: `- **时间复杂度**：平均 $O(N \log N)$；最坏情况下基准点选择不当，时间复杂度退化为 $O(N^2)$。\n- **空间复杂度**：平均为 $O(\log N)$，指的是分治递归时所消耗的空间。`,
        code: `function quickSort(arr) {\n    if (arr.length <= 1) return arr;\n    const pivot = arr[Math.floor(arr.length / 2)];\n    const left = [];\n    const middle = [];\n    const right = [];\n    for (let val of arr) {\n        if (val < pivot) left.push(val);\n        else if (val === pivot) middle.push(val);\n        else right.push(val);\n    }\n    return [...quickSort(left), ...middle, ...quickSort(right)];\n}`
    },
    binary_search: {
        complexity: `- **时间复杂度**：$O(\log N)$，由于折半收缩边界，运行速度极快。\n- **空间复杂度**：$O(1)$，常数空间迭代法。`,
        code: `function search(nums, target) {\n    let left = 0;\n    let right = nums.length - 1;\n    while (left <= right) {\n        const mid = left + Math.floor((right - left) / 2);\n        if (nums[mid] === target) return mid;\n        else if (nums[mid] < target) left = mid + 1;\n        else right = mid - 1;\n    }\n    return -1;\n}`
    },
    merge_intervals: {
        complexity: `- **时间复杂度**：$O(N \log N)$，主要开销在于将区间按起始位置升序排列。\n- **空间复杂度**：$O(\log N)$，归并或快速排序的空间复杂度开销。`,
        code: `function merge(intervals) {\n    if (intervals.length === 0) return [];\n    intervals.sort((a, b) => a[0] - b[0]);\n    const merged = [intervals[0]];\n    for (let i = 1; i < intervals.length; i++) {\n        const curr = intervals[i];\n        const last = merged[merged.length - 1];\n        if (curr[0] <= last[1]) {\n            last[1] = Math.max(last[1], curr[1]);\n        } else {\n            merged.push(curr);\n        }\n    }\n    return merged;\n}`
    },
    search_rotated: {
        complexity: `- **时间复杂度**：$O(\log N)$。通过判断区间左半边或右半边是否有序，可以实现一次折半查找。\n- **空间复杂度**：$O(1)$。`,
        code: `function searchRotated(nums, target) {\n    let left = 0, right = nums.length - 1;\n    while (left <= right) {\n        const mid = left + Math.floor((right - left) / 2);\n        if (nums[mid] === target) return mid;\n        if (nums[left] <= nums[mid]) {\n            if (nums[left] <= target && target < nums[mid]) right = mid - 1;\n            else left = mid + 1;\n        } else {\n            if (nums[mid] < target && target <= nums[right]) left = mid + 1;\n            else right = mid - 1;\n        }\n    }\n    return -1;\n}`
    },

    // === 大类 5：字符串与双指针 ===
    is_palindrome: {
        complexity: `- **时间复杂度**：$O(N)$，清理多余字符后，使用对撞双指针分别向内扫描。\n- **空间复杂度**：$O(1)$，常数级别辅助空间。`,
        code: `function isPalindrome(s) {\n    const clean = s.toLowerCase().replace(/[^a-z0-9]/g, '');\n    let left = 0, right = clean.length - 1;\n    while (left < right) {\n        if (clean[left] !== clean[right]) return false;\n        left++;\n        right--;\n    }\n    return true;\n}`
    },
    longest_substring: {
        complexity: `- **时间复杂度**：$O(N)$，右指针遍历字符串，左指针自适应缩紧，每个字符最多被访问两次。\n- **空间复杂度**：$O(\min(M, N))$，使用哈希集合保存滑动窗口内的非重复字符。`,
        code: `function lengthOfLongestSubstring(s) {\n    const set = new Set();\n    let left = 0, maxLen = 0;\n    for (let r = 0; r < s.length; r++) {\n        while (set.has(s[r])) {\n            set.delete(s[left]);\n            left++;\n        }\n        set.add(s[r]);\n        maxLen = Math.max(maxLen, r - left + 1);\n    }\n    return maxLen;\n}`
    },
    max_area: {
        complexity: `- **时间复杂度**：$O(N)$，双指针分别由两侧边界相向运动，每次舍弃高度较矮的一侧。\n- **空间复杂度**：$O(1)$。`,
        code: `function maxArea(height) {\n    let left = 0, right = height.length - 1;\n    let max = 0;\n    while (left < right) {\n        const area = Math.min(height[left], height[right]) * (right - left);\n        max = Math.max(max, area);\n        if (height[left] < height[right]) left++;\n        else right--;\n    }\n    return max;\n}`
    },
    three_sum: {
        complexity: `- **时间复杂度**：$O(N^2)$，首先升序排列，然后使用单层循环结合双指针相向逼近，实现快速查重。\n- **空间复杂度**：$O(\log N)$，主要是排序所需的空间开销。`,
        code: `function threeSum(nums) {\n    nums.sort((a, b) => a - b);\n    const res = [];\n    for (let i = 0; i < nums.length - 2; i++) {\n        if (i > 0 && nums[i] === nums[i - 1]) continue;\n        let left = i + 1, right = nums.length - 1;\n        while (left < right) {\n            const sum = nums[i] + nums[left] + nums[right];\n            if (sum === 0) {\n                res.push([nums[i], nums[left], nums[right]]);\n                while (left < right && nums[left] === nums[left + 1]) left++;\n                while (left < right && nums[right] === nums[right - 1]) right--;\n                left++;\n                right--;\n            } else if (sum < 0) left++;\n            else right--;\n        }\n    }\n    return res;\n}`
    },
    min_window: {
        complexity: `- **时间复杂度**：$O(N+M)$，其中 N 和 M 为两个字符串长度，滑动窗口经典应用。\n- **空间复杂度**：$O(K)$，K 为英文字符集大小（通常为常数 52）。`,
        code: `function minWindow(s, t) {\n    const need = {}, window = {};\n    for (let char of t) need[char] = (need[char] || 0) + 1;\n    let left = 0, right = 0, valid = 0;\n    let start = 0, minLen = Infinity;\n    const requiredSize = Object.keys(need).length;\n    while (right < s.length) {\n        const c = s[right];\n        right++;\n        if (c in need) {\n            window[c] = (window[c] || 0) + 1;\n            if (window[c] === need[c]) valid++;\n        }\n        while (valid === requiredSize) {\n            if (right - left < minLen) {\n                start = left;\n                minLen = right - left;\n            }\n            const d = s[left];\n            left++;\n            if (d in need) {\n                if (window[d] === need[d]) valid--;\n                window[d]--;\n            }\n        }\n    }\n    return minLen === Infinity ? "" : s.substring(start, start + minLen);\n}`
    },

    // === 大类 6：动态规划 ===
    fibonacci: {
        complexity: `- **时间复杂度**：$O(N)$，相较于递归实现的 $O(2^N)$ 效率有了极大飞跃。\n- **空间复杂度**：$O(1)$，通过滚动保存上两个状态值，降至常数级空间开销。`,
        code: `function fibonacci(n) {\n    if (n < 2) return n;\n    let p = 0, q = 1;\n    for (let i = 2; i <= n; i++) {\n        let temp = p + q;\n        p = q;\n        q = temp;\n    }\n    return q;\n}`
    },
    climb_stairs: {
        complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(1)$，属于斐波那契数演变题，使用动态规划滚动迭代即可。`,
        code: `function climbStairs(n) {\n    if (n <= 2) return n;\n    let p = 1, q = 2;\n    for (let i = 3; i <= n; i++) {\n        let temp = p + q;\n        p = q;\n        q = temp;\n    }\n    return q;\n}`
    },
    max_sub_array: {
        complexity: `- **时间复杂度**：$O(N)$，只需遍历一次数组即可（Kadane's 算法）。\n- **空间复杂度**：$O(1)$，仅需局部最大和全局最大两个变量同步维护。`,
        code: `function maxSubArray(nums) {\n    let pre = 0, maxAns = nums[0];\n    nums.forEach((x) => {\n        pre = Math.max(pre + x, x);\n        maxAns = Math.max(maxAns, pre);\n    });\n    return maxAns;\n}`
    },
    coin_change: {
        complexity: `- **时间复杂度**：$O(S \times N)$，S 是总金额，N 是面额种类。\n- **空间复杂度**：$O(S)$，建立长度为 $S+1$ 的动态规划数组。`,
        code: `function coinChange(coins, amount) {\n    const dp = new Array(amount + 1).fill(Infinity);\n    dp[0] = 0;\n    for (let i = 1; i <= amount; i++) {\n        for (let coin of coins) {\n            if (i >= coin) {\n                dp[i] = Math.min(dp[i], dp[i - coin] + 1);\n            }\n        }\n    }\n    return dp[amount] === Infinity ? -1 : dp[amount];\n}`
    },
    longest_lis: {
        complexity: `- **时间复杂度**：$O(N^2)$；如果采用贪心加二分搜索策略，可以优化至 $O(N \log N)$。\n- **空间复杂度**：$O(N)$。`,
        code: `function lengthOfLIS(nums) {\n    if (nums.length === 0) return 0;\n    const dp = new Array(nums.length).fill(1);\n    let max = 1;\n    for (let i = 1; i < nums.length; i++) {\n        for (let j = 0; j < i; j++) {\n            if (nums[i] > nums[j]) {\n                dp[i] = Math.max(dp[i], dp[j] + 1);\n            }\n        }\n        max = Math.max(max, dp[i]);\n    }\n    return max;\n}`
    },

    // === 大类 7：贪心与回溯 ===
    max_profit: {
        complexity: `- **时间复杂度**：$O(N)$，一次遍历。在遍历时动态更新历史最低点并计算可能的最大收益。\n- **空间复杂度**：$O(1)$。`,
        code: `function maxProfit(prices) {\n    let minPrice = Infinity;\n    let maxProfit = 0;\n    for (let price of prices) {\n        if (price < minPrice) {\n            minPrice = price;\n        } else if (price - minPrice > maxProfit) {\n            maxProfit = price - minPrice;\n        }\n    }\n    return maxProfit;\n}`
    },
    can_jump: {
        complexity: `- **时间复杂度**：$O(N)$，从头到尾贪心寻找当前能够到达的最大覆盖范围。\n- **空间复杂度**：$O(1)$。`,
        code: `function canJump(nums) {\n    let maxReach = 0;\n    for (let i = 0; i < nums.length; i++) {\n        if (i > maxReach) return false;\n        maxReach = Math.max(maxReach, i + nums[i]);\n    }\n    return true;\n}`
    },
    permute: {
        complexity: `- **时间复杂度**：$O(N \times N!)$，递归搜索树的叶子结点为全排列总量 $N!$。\n- **空间复杂度**：$O(N)$，主要是回溯递归时栈的最大空间开销。`,
        code: `function permute(nums) {\n    const res = [];\n    const path = [];\n    const used = {};\n    function dfs() {\n        if (path.length === nums.length) {\n            res.push([...path]);\n            return;\n        }\n        for (let num of nums) {\n            if (used[num]) continue;\n            path.push(num);\n            used[num] = true;\n            dfs();\n            path.pop();\n            used[num] = false;\n        }\n    }\n    dfs();\n    return res;\n}`
    },
    subsets: {
        complexity: `- **时间复杂度**：$O(N \times 2^N)$，每个数存在“选与不选”两种路径分支。\n- **空间复杂度**：$O(N)$，回溯调用的递归深度上限。`,
        code: `function subsets(nums) {\n    const res = [];\n    const path = [];\n    function dfs(index) {\n        res.push([...path]);\n        for (let i = index; i < nums.length; i++) {\n            path.push(nums[i]);\n            dfs(i + 1);\n            path.pop();\n        }\n    }\n    dfs(0);\n    return res;\n}`
    },
    generate_parentheses: {
        complexity: `- **时间复杂度**：卡特兰数级别，$O(\frac{4^N}{N \sqrt{N}})$。\n- **空间复杂度**：$O(N)$，主要为深度优先遍历产生的最大递归深度。`,
        code: `function generateParenthesis(n) {\n    const res = [];\n    function dfs(left, right, str) {\n        if (str.length === n * 2) {\n            res.push(str);\n            return;\n        }\n        if (left < n) dfs(left + 1, right, str + '(');\n        if (right < left) dfs(left, right + 1, str + ')');\n    }\n    dfs(0, 0, "");\n    return res;\n}`
    },

    // === 大类 8：数学与趣味算法 ===
    single_number: {
        complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(1)$，通过异或运算的自反律 $A \oplus A = 0$ 和同一律 $A \oplus 0 = A$，巧妙完成了零额外空间的查找。`,
        code: `function singleNumber(nums) {\n    let ans = 0;\n    for (let num of nums) {\n        ans ^= num;\n    }\n    return ans;\n}`
    },
    majority_element: {
        complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(1)$，运用经典的摩尔投票算法（Boyer-Moore Voting），通过不同正负值相互抵消来求绝对多数。`,
        code: `function majorityElement(nums) {\n    let count = 0;\n    let candidate = null;\n    for (let num of nums) {\n        if (count === 0) candidate = num;\n        count += (num === candidate) ? 1 : -1;\n    }\n    return candidate;\n}`
    },
    is_happy: {
        complexity: `- **时间复杂度**：$O(\log N)$。\n- **空间复杂度**：$O(1)$，若采用快慢指针的思路进行“环形检测”，则无任何额外开销；若使用哈希法则为 $O(\log N)$。`,
        code: `function isHappy(n) {\n    const getNext = (num) => {\n        let sum = 0;\n        while (num > 0) {\n            const d = num % 10;\n            sum += d * d;\n            num = Math.floor(num / 10);\n        }\n        return sum;\n    };\n    let slow = n, fast = getNext(n);\n    while (fast !== 1 && slow !== fast) {\n        slow = getNext(slow);\n        fast = getNext(getNext(fast));\n    }\n    return fast === 1;\n}`
    },
    plus_one: {
        complexity: `- **时间复杂度**：$O(N)$。\n- **空间复杂度**：$O(1)$，除非遇到全部为 9 的数组需要重新分配一个长为 $N+1$ 的空间。`,
        code: `function plusOne(digits) {\n    for (let i = digits.length - 1; i >= 0; i--) {\n        digits[i]++;\n        digits[i] %= 10;\n        if (digits[i] !== 0) {\n            return digits;\n        }\n    }\n    return [1, ...digits];\n}`
    },
    roman_to_int: {
        complexity: `- **时间复杂度**：$O(N)$，扫描罗马字符串一次。\n- **空间复杂度**：$O(1)$。`,
        code: `function romanToInt(s) {\n    const map = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };\n    let sum = 0;\n    for (let i = 0; i < s.length; i++) {\n        const val = map[s[i]];\n        const nextVal = map[s[i+1]];\n        if (nextVal && val < nextVal) {\n            sum -= val;\n        } else {\n            sum += val;\n        }\n    }\n    return sum;\n}`
    },
    // === 大类 1 困难题 ===
    merge_k_lists: {
        complexity: `- **时间复杂度**：$O(N \log K)$，其中 N 是所有链表节点的总数，K 是链表的个数。分治合并或使用最小堆均可达到此复杂度。\n- **空间复杂度**：$O(\log K)$ 递归栈空间，或 $O(K)$ 堆空间。`,
        code: `function mergeKLists(lists) {\n    if (lists.length === 0) return null;\n    function merge2(l1, l2) {\n        let dummy = { val: 0, next: null };\n        let curr = dummy;\n        while (l1 && l2) {\n            if (l1.val <= l2.val) { curr.next = l1; l1 = l1.next; }\n            else { curr.next = l2; l2 = l2.next; }\n            curr = curr.next;\n        }\n        curr.next = l1 || l2;\n        return dummy.next;\n    }\n    function divide(l, r) {\n        if (l === r) return lists[l];\n        const mid = (l + r) >> 1;\n        return merge2(divide(l, mid), divide(mid + 1, r));\n    }\n    return divide(0, lists.length - 1);\n}`
    },
    reverse_k_group: {
        complexity: `- **时间复杂度**：$O(N)$，链表中的每个节点最多被翻转两次（分组翻转以及不足K个保持顺序）。\n- **空间复杂度**：$O(N/k)$，递归调用深度产生的额外栈空间。`,
        code: `function reverseKGroup(head, k) {\n    let curr = head;\n    let count = 0;\n    while (curr && count !== k) {\n        curr = curr.next;\n        count++;\n    }\n    if (count === k) {\n        let prev = reverseKGroup(curr, k);\n        while (count-- > 0) {\n            let temp = head.next;\n            head.next = prev;\n            prev = head;\n            head = temp;\n        }\n        head = prev;\n    }\n    return head;\n}`
    },
    find_median_sorted_arrays: {
        complexity: `- **时间复杂度**：$O(\log(M+N))$，其中 M 和 N 是两个数组的长度。采用二分法排除不合格的部分，效率极高。\n- **空间复杂度**：$O(1)$，仅需常数级别临时变量。`,
        code: `function findMedianSortedArrays(nums1, nums2) {\n    const total = nums1.length + nums2.length;\n    if (total % 2 === 1) {\n        return getKthElement(nums1, nums2, Math.floor(total / 2) + 1);\n    } else {\n        return (getKthElement(nums1, nums2, total / 2) + getKthElement(nums1, nums2, total / 2 + 1)) / 2.0;\n    }\n    function getKthElement(arr1, arr2, k) {\n        let idx1 = 0, idx2 = 0;\n        while (true) {\n            if (idx1 === arr1.length) return arr2[idx2 + k - 1];\n            if (idx2 === arr2.length) return arr1[idx1 + k - 1];\n            if (k === 1) return Math.min(arr1[idx1], arr2[idx2]);\n            let half = Math.floor(k / 2);\n            let newIdx1 = Math.min(idx1 + half, arr1.length) - 1;\n            let newIdx2 = Math.min(idx2 + half, arr2.length) - 1;\n            if (arr1[newIdx1] <= arr2[newIdx2]) {\n                k -= (newIdx1 - idx1 + 1);\n                idx1 = newIdx1 + 1;\n            } else {\n                k -= (newIdx2 - idx2 + 1);\n                idx2 = newIdx2 + 1;\n            }\n        }\n    }\n}`
    },

    // === 大类 2 困难题 ===
    trap: {
        complexity: `- **时间复杂度**：$O(N)$，扫描一遍高度数组，利用双指针或者单调栈进行雨水积存的计算。\n- **空间复杂度**：$O(1)$，若采用双指针法则为原地计算。`,
        code: `function trap(height) {\n    let left = 0, right = height.length - 1;\n    let leftMax = 0, rightMax = 0;\n    let water = 0;\n    while (left < right) {\n        if (height[left] < height[right]) {\n            if (height[left] >= leftMax) leftMax = height[left];\n            else water += (leftMax - height[left]);\n            left++;\n        } else {\n            if (height[right] >= rightMax) rightMax = height[right];\n            else water += (rightMax - height[right]);\n            right--;\n        }\n    }\n    return water;\n}`
    },
    largest_rectangle_area: {
        complexity: `- **时间复杂度**：$O(N)$，利用单调栈（维持高度单调递增），每个高度最多入栈出栈一次。\n- **空间复杂度**：$O(N)$，用于维护单调栈的存储空间。`,
        code: `function largestRectangleArea(heights) {\n    const stack = [];\n    let maxArea = 0;\n    const h = [0, ...heights, 0]; // 哨兵节点简化边界判定\n    for (let i = 0; i < h.length; i++) {\n        while (stack.length > 0 && h[i] < h[stack[stack.length - 1]]) {\n            const currH = h[stack.pop()];\n            const width = i - stack[stack.length - 1] - 1;\n            maxArea = Math.max(maxArea, currH * width);\n        }\n        stack.push(i);\n    }\n    return maxArea;\n}`
    },
    maximal_rectangle: {
        complexity: `- **时间复杂度**：$O(R \times C)$，其中 R 为行数，C 为列数。对每一行进行动态高度统计，复用单调栈求解最大柱状面积。\n- **空间复杂度**：$O(C)$，维护当前行柱体的高度数组。`,
        code: `function maximalRectangle(matrix) {\n    if (matrix.length === 0 || matrix[0].length === 0) return 0;\n    const cols = matrix[0].length;\n    const heights = new Array(cols).fill(0);\n    let maxArea = 0;\n    for (let row = 0; row < matrix.length; row++) {\n        for (let col = 0; col < cols; col++) {\n            heights[col] = matrix[row][col] === '1' ? heights[col] + 1 : 0;\n        }\n        maxArea = Math.max(maxArea, getMaxArea(heights));\n    }\n    return maxArea;\n    function getMaxArea(hArr) {\n        const s = [];\n        let max = 0;\n        const extendedH = [0, ...hArr, 0];\n        for (let i = 0; i < extendedH.length; i++) {\n            while (s.length > 0 && extendedH[i] < extendedH[s[s.length - 1]]) {\n                const height = extendedH[s.pop()];\n                const width = i - s[s.length - 1] - 1;\n                max = Math.max(max, height * width);\n            }\n            s.push(i);\n        }\n        return max;\n    }\n}`
    },

    // === 大类 3 困难题 ===
    max_path_sum: {
        complexity: `- **时间复杂度**：$O(N)$，递归遍历二叉树中的每个节点，并动态累加最大单向路径贡献值。\n- **空间复杂度**：$O(H)$，H 为树的高度，递归系统的栈深度开销。`,
        code: `function maxPathSum(root) {\n    let maxSum = -Infinity;\n    function getContribution(node) {\n        if (!node) return 0;\n        const left = Math.max(getContribution(node.left), 0);\n        const right = Math.max(getContribution(node.right), 0);\n        maxSum = Math.max(maxSum, node.val + left + right);\n        return node.val + Math.max(left, right);\n    }\n    getContribution(root);\n    return maxSum;\n}`
    },
    serialize_deserialize: {
        complexity: `- **时间复杂度**：序列化和反序列化均为 $O(N)$，对树节点做 DFS 字符串拼装与解析。\n- **空间复杂度**：$O(N)$，需要存储序列化串解析结果。`,
        code: `function testCodec(root) {\n    function serialize(node) {\n        if (!node) return '#';\n        return node.val + ',' + serialize(node.left) + ',' + serialize(node.right);\n    }\n    function deserialize(str) {\n        const vals = str.split(',');\n        let i = 0;\n        function build() {\n            if (i >= vals.length || vals[i] === '#') { i++; return null; }\n            let node = { val: Number(vals[i++]), left: null, right: null };\n            node.left = build();\n            node.right = build();\n            return node;\n        }\n        return build();\n    }\n    return deserialize(serialize(root));\n}`
    },
    min_camera_cover: {
        complexity: `- **时间复杂度**：$O(N)$，自底向上进行状态传递，根据三个核心监控状态采取贪心装配摄像头。\n- **空间复杂度**：$O(H)$。`,
        code: `function minCameraCover(root) {\n    let cameras = 0;\n    // 状态定义: 0-无覆盖, 1-有相机覆盖, 2-已被相机监视但无自身相机\n    function dfs(node) {\n        if (!node) return 2;\n        const l = dfs(node.left);\n        const r = dfs(node.right);\n        if (l === 0 || r === 0) {\n            cameras++;\n            return 1;\n        }\n        if (l === 1 || r === 1) return 2;\n        return 0;\n    }\n    if (dfs(root) === 0) cameras++;\n    return cameras;\n}`
    },

    // === 大类 4 困难题 ===
    median_finder: {
        complexity: `- **时间复杂度**：添加元素 addNum 为 $O(\log N)$，获取中位数 findMedian 为 $O(1)$，通过维护大小根堆可得此复杂度。本地采用二分查找插入排序模拟此流程。\n- **空间复杂度**：$O(N)$，存储当前数据流所有元素。`,
        code: `function testMedianFinder(commands, values) {\n    class MedianFinder {\n        constructor() { this.nums = []; }\n        addNum(num) {\n            let l = 0, r = this.nums.length - 1;\n            while (l <= r) {\n                let mid = (l + r) >> 1;\n                if (this.nums[mid] < num) l = mid + 1;\n                else r = mid - 1;\n            }\n            this.nums.splice(l, 0, num);\n        }\n        findMedian() {\n            let n = this.nums.length;\n            if (n % 2 === 1) return this.nums[Math.floor(n / 2)];\n            return (this.nums[n / 2 - 1] + this.nums[n / 2]) / 2;\n        }\n    }\n    const finder = new MedianFinder();\n    const out = [];\n    commands.forEach((cmd, i) => {\n        if (cmd === 'addNum') finder.addNum(values[i]);\n        else if (cmd === 'findMedian') out.push(finder.findMedian());\n    });\n    return out;\n}`
    },
    count_range_sum: {
        complexity: `- **时间复杂度**：$O(N \log N)$，可以采用归并排序中分治计算区间前缀和的落点区间个数，或者采用线段树。\n- **空间复杂度**：$O(N)$。`,
        code: `function countRangeSum(nums, lower, upper) {\n    let count = 0;\n    const sums = [0];\n    for (let num of nums) sums.push(sums[sums.length - 1] + num);\n    function mergeSort(l, r) {\n        if (l === r) return;\n        const mid = (l + r) >> 1;\n        mergeSort(l, mid);\n        mergeSort(mid + 1, r);\n        // 统计区间和个数\n        let i = l, j = l;\n        for (let k = mid + 1; k <= r; k++) {\n            while (i <= mid && sums[k] - sums[i] > upper) i++;\n            while (j <= mid && sums[k] - sums[j] >= lower) j++;\n            count += (j - i);\n        }\n        // 原地归并两段有序前缀和数组\n        const sorted = [];\n        let p1 = l, p2 = mid + 1;\n        while (p1 <= mid || p2 <= r) {\n            if (p1 > mid) sorted.push(sums[p2++]);\n            else if (p2 > r) sorted.push(sums[p1++]);\n            else sorted.push(sums[p1] < sums[p2] ? sums[p1++] : sums[p2++]);\n        }\n        for (let idx = 0; idx < sorted.length; idx++) sums[l + idx] = sorted[idx];\n    }\n    mergeSort(0, sums.length - 1);\n    return count;\n}`
    },
    find_min_ii: {
        complexity: `- **时间复杂度**：平均 $O(\log N)$，但在遇到大量重复边界值时（如 \`[2,2,2,0,2]\`）会退化至 $O(N)$。\n- **空间复杂度**：$O(1)$，常数原地定位。`,
        code: `function findMin(nums) {\n    let l = 0, r = nums.length - 1;\n    while (l < r) {\n        const mid = (l + r) >> 1;\n        if (nums[mid] < nums[r]) r = mid;\n        else if (nums[mid] > nums[r]) l = mid + 1;\n        else r--; // 无法确定单调侧，缩减右边界\n    }\n    return nums[l];\n}`
    },

    // === 大类 5 困难题 ===
    is_match: {
        complexity: `- **时间复杂度**：$O(M \times N)$，其中 M 和 N 是输入字符串与正则表达式的长度。\n- **空间复杂度**：$O(M \times N)$，用于存储状态推导的 DP 二维矩阵空间。`,
        code: `function isMatch(s, p) {\n    const m = s.length, n = p.length;\n    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(false));\n    dp[0][0] = true;\n    for (let j = 1; j <= n; j++) {\n        if (p[j - 1] === '*') dp[0][j] = dp[0][j - 2];\n    }\n    for (let i = 1; i <= m; i++) {\n        for (let j = 1; j <= n; j++) {\n            if (p[j - 1] === '.' || p[j - 1] === s[i - 1]) {\n                dp[i][j] = dp[i - 1][j - 1];\n            } else if (p[j - 1] === '*') {\n                dp[i][j] = dp[i][j - 2];\n                if (p[j - 2] === '.' || p[j - 2] === s[i - 1]) {\n                    dp[i][j] = dp[i][j] || dp[i - 1][j];\n                }\n            }\n        }\n    }\n    return dp[m][n];\n}`
    },
    min_distance: {
        complexity: `- **时间复杂度**：$O(M \times N)$，两个单词长度的乘积。\n- **空间复杂度**：$O(M \times N)$，经典编辑匹配转移矩阵。`,
        code: `function minDistance(word1, word2) {\n    const m = word1.length, n = word2.length;\n    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));\n    for (let i = 0; i <= m; i++) dp[i][0] = i;\n    for (let j = 0; j <= n; j++) dp[0][j] = j;\n    for (let i = 1; i <= m; i++) {\n        for (let j = 1; j <= n; j++) {\n            if (word1[i - 1] === word2[j - 1]) {\n                dp[i][j] = dp[i - 1][j - 1];\n            } else {\n                dp[i][j] = Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1;\n            }\n        }\n    }\n    return dp[m][n];\n}`
    },
    find_substring: {
        complexity: `- **时间复杂度**：$O(N \times M)$，N 为长串长度，M 为单词总数乘长度，采用哈希表统计与滑动窗口实现优化。\n- **空间复杂度**：$O(M)$。`,
        code: `function findSubstring(s, words) {\n    if (s.length === 0 || words.length === 0) return [];\n    const wordLen = words[0].length;\n    const wordNum = words.length;\n    const allWordsLen = wordLen * wordNum;\n    const res = [];\n    const map = {};\n    for (let w of words) map[w] = (map[w] || 0) + 1;\n    for (let i = 0; i < s.length - allWordsLen + 1; i++) {\n        const sub = s.substring(i, i + allWordsLen);\n        const tempMap = {};\n        let j = 0;\n        while (j < wordNum) {\n            const word = sub.substring(j * wordLen, (j + 1) * wordLen);\n            if (word in map) {\n                tempMap[word] = (tempMap[word] || 0) + 1;\n                if (tempMap[word] > map[word]) break;\n            } else {\n                break;\n            }\n            j++;\n        }\n        if (j === wordNum) res.push(i);\n    }\n    return res;\n}`
    },

    // === 大类 6 困难题 ===
    max_profit_iv: {
        complexity: `- **时间复杂度**：$O(N \times K)$，通过扩展每日持有和不持有状态转换实现股票利润转移方程。\n- **空间复杂度**：$O(K)$ 状态空间。`,
        code: `function maxProfitIV(k, prices) {\n    if (prices.length === 0) return 0;\n    const n = prices.length;\n    k = Math.min(k, Math.floor(n / 2));\n    const buy = new Array(k + 1).fill(-Infinity);\n    const sell = new Array(k + 1).fill(0);\n    for (let p of prices) {\n        for (let i = 1; i <= k; i++) {\n            buy[i] = Math.max(buy[i], sell[i - 1] - p);\n            sell[i] = Math.max(sell[i], buy[i] + p);\n        }\n    }\n    return sell[k];\n}`
    },
    max_coins: {
        complexity: `- **时间复杂度**：$O(N^3)$，属于区间型动态规划的经典应用，需要三层循环来枚举区间的起点、终点和最后戳破的气球。\n- **空间复杂度**：$O(N^2)$。`,
        code: `function maxCoins(nums) {\n    const n = nums.length;\n    const points = [1, ...nums, 1];\n    const dp = Array.from({ length: n + 2 }, () => new Array(n + 2).fill(0));\n    for (let i = n; i >= 0; i--) {\n        for (let j = i + 1; j <= n + 1; j++) {\n            for (let k = i + 1; k < j; k++) {\n                dp[i][j] = Math.max(dp[i][j], dp[i][k] + dp[k][j] + points[i] * points[k] * points[j]);\n            }\n        }\n    }\n    return dp[0][n + 1];\n}`
    },
    calculate_minimum_hp: {
        complexity: `- **时间复杂度**：$O(R \times C)$，自右下角向左上角进行逆向动态规划状态推导，以保障局部状态解为全局所采纳。\n- **空间复杂度**：$O(R \times C)$，可压缩至 $O(C)$。`,
        code: `function calculateMinimumHP(dungeon) {\n    const r = dungeon.length, c = dungeon[0].length;\n    const dp = Array.from({ length: r + 1 }, () => new Array(c + 1).fill(Infinity));\n    dp[r][c - 1] = 1; dp[r - 1][c] = 1;\n    for (let i = r - 1; i >= 0; i--) {\n        for (let j = c - 1; j >= 0; j--) {\n            const minNeed = Math.min(dp[i + 1][j], dp[i][j + 1]) - dungeon[i][j];\n            dp[i][j] = Math.max(minNeed, 1);\n        }\n    }\n    return dp[0][0];\n}`
    },

    // === 大类 7 困难题 ===
    solve_n_queens: {
        complexity: `- **时间复杂度**：$O(N!)$，每一行皇后的可选列数依次递减，并配合强力的剪枝判断。\n- **空间复杂度**：$O(N)$，递归系统调用的路径记录与冲突标记。`,
        code: `function solveNQueens(n) {\n    const res = [];\n    const cols = new Set(), diag1 = new Set(), diag2 = new Set();\n    const board = Array.from({ length: n }, () => new Array(n).fill('.'));\n    function backtrack(r) {\n        if (r === n) {\n            res.push(board.map(row => row.join('')));\n            return;\n        }\n        for (let c = 0; c < n; c++) {\n            if (cols.has(c) || diag1.has(r - c) || diag2.has(r + c)) continue;\n            board[r][c] = 'Q';\n            cols.add(c); diag1.add(r - c); diag2.add(r + c);\n            backtrack(r + 1);\n            board[r][c] = '.';\n            cols.delete(c); diag1.delete(r - c); diag2.delete(r + c);\n        }\n    }\n    backtrack(0);\n    return res;\n}`
    },
    solve_sudoku: {
        complexity: `- **时间复杂度**：$O(9^{81})$（最坏情况，但实际上由于数独的初始提示数，剪枝非常强力，通常毫秒级出解）。\n- **空间复杂度**：$O(81)$。`,
        code: `function testSudoku(board) {\n    function solve(b) {\n        for (let r = 0; r < 9; r++) {\n            for (let c = 0; c < 9; c++) {\n                if (b[r][c] === '.') {\n                    for (let val = 1; val <= 9; val++) {\n                        const charVal = String(val);\n                        if (isValid(b, r, c, charVal)) {\n                            b[r][c] = charVal;\n                            if (solve(b)) return true;\n                            b[r][c] = '.';\n                        }\n                    }\n                    return false;\n                }\n            }\n        }\n        return true;\n    }\n    function isValid(b, row, col, char) {\n        for (let i = 0; i < 9; i++) {\n            if (b[row][i] === char) return false;\n            if (b[i][col] === char) return false;\n            const boxRow = 3 * Math.floor(row / 3) + Math.floor(i / 3);\n            const boxCol = 3 * Math.floor(col / 3) + (i % 3);\n            if (b[boxRow][boxCol] === char) return false;\n        }\n        return true;\n    }\n    const boardClone = JSON.parse(JSON.stringify(board));\n    solve(boardClone);\n    return boardClone;\n}`
    },
    find_ladders: {
        complexity: `- **时间复杂度**：$O(N \times 26^L)$，其中 N 为单词列表长度，L 为单词长度。采用 BFS 双向搜索或带状态压缩的记录获取全部最短接龙方案。\n- **空间复杂度**：$O(N \times L)$。`,
        code: `function findLadders(beginWord, endWord, wordList) {\n    const wordSet = new Set(wordList);\n    if (!wordSet.has(endWord)) return [];\n    const res = [];\n    const from = new Map(); // 记录每个单词的前驱列表\n    const steps = new Map(); // 记录到达每个单词的最短步数\n    steps.set(beginWord, 0);\n    const queue = [beginWord];\n    let found = false;\n    let step = 0;\n    while (queue.length > 0) {\n        step++;\n        const size = queue.length;\n        for (let i = 0; i < size; i++) {\n            const curr = queue.shift();\n            const currStep = steps.get(curr);\n            for (let j = 0; j < curr.length; j++) {\n                const originalChar = curr[j];\n                for (let c = 97; c <= 122; c++) {\n                    const charVal = String.fromCharCode(c);\n                    if (charVal === originalChar) continue;\n                    const nextWord = curr.slice(0, j) + charVal + curr.slice(j + 1);\n                    if (wordSet.has(nextWord)) {\n                        if (!steps.has(nextWord)) {\n                            steps.set(nextWord, step);\n                            queue.push(nextWord);\n                        }\n                        if (steps.get(nextWord) === step) {\n                            if (!from.has(nextWord)) from.set(nextWord, []);\n                            from.get(nextWord).push(curr);\n                        }\n                        if (nextWord === endWord) found = true;\n                    }\n                }\n            }\n        }\n        if (found) break;\n    }\n    if (found) {\n        const path = [endWord];\n        dfs(endWord, path);\n    }\n    function dfs(word, path) {\n        if (word === beginWord) {\n            res.push([...path].reverse());\n            return;\n        }\n        const parents = from.get(word) || [];\n        for (let p of parents) {\n            path.push(p);\n            dfs(p, path);\n            path.pop();\n        }\n    }\n    return res;\n}`
    },

    // === 大类 8 困难题 ===
    max_points: {
        complexity: `- **时间复杂度**：$O(N^2)$，因为需要枚举所有的点两两组合的斜率，并利用哈希表统计最大共线点数。\n- **空间复杂度**：$O(N)$，统计每个点出发的斜率哈希空间。`,
        code: `function maxPoints(points) {\n    if (points.length <= 2) return points.length;\n    let max = 0;\n    for (let i = 0; i < points.length; i++) {\n        const slopes = new Map();\n        let samePoint = 1;\n        let localMax = 0;\n        for (let j = i + 1; j < points.length; j++) {\n            const dy = points[j][1] - points[i][1];\n            const dx = points[j][0] - points[i][0];\n            const g = gcd(dy, dx);\n            const key = (dy / g) + '/' + (dx / g);\n            slopes.set(key, (slopes.get(key) || 0) + 1);\n            localMax = Math.max(localMax, slopes.get(key));\n        }\n        max = Math.max(max, localMax + samePoint);\n    }\n    return max;\n    function gcd(a, b) {\n        return b === 0 ? a : gcd(b, a % b);\n    }\n}`
    },
    number_to_words: {
        complexity: `- **时间复杂度**：$O(1)$，由于整数范围限制在三十二位，最大为十亿级，转换过程由常数级段落拼接组成。\n- **空间复杂度**：$O(1)$。`,
        code: `function numberToWords(num) {\n    if (num === 0) return "Zero";\n    const singles = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];\n    const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];\n    const thousands = ["", "Thousand", "Million", "Billion"];\n    let res = "";\n    let idx = 0;\n    while (num > 0) {\n        if (num % 1000 !== 0) {\n            res = helper(num % 1000) + (thousands[idx] ? " " + thousands[idx] : "") + (res ? " " + res : "");\n        }\n        num = Math.floor(num / 1000);\n        idx++;\n    }\n    return res.trim();\n    function helper(n) {\n        if (n === 0) return "";\n        else if (n < 20) return singles[n];\n        else if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? " " + singles[n % 10] : "");\n        else return singles[Math.floor(n / 100)] + " Hundred" + (n % 100 ? " " + helper(n % 100) : "");\n    }\n}`
    },
    nth_super_ugly_number: {
        complexity: `- **时间复杂度**：$O(N \times K)$，其中 K 是 primes 的长度。利用动态指针数组对每一个丑数的生成进行多路归并推进。\n- **空间复杂度**：$O(N + K)$，存储前缀丑数列表以及指针和预计算数组。`,
        code: `function nthSuperUglyNumber(n, primes) {\n    const dp = new Array(n).fill(0);\n    dp[0] = 1;\n    const m = primes.length;\n    const pointers = new Array(m).fill(0);\n    for (let i = 1; i < n; i++) {\n        let minVal = Infinity;\n        for (let j = 0; j < m; j++) {\n            minVal = Math.min(minVal, dp[pointers[j]] * primes[j]);\n        }\n        dp[i] = minVal;\n        for (let j = 0; j < m; j++) {\n            if (dp[pointers[j]] * primes[j] === minVal) {\n                pointers[j]++;\n            }\n        }\n    }\n    return dp[n - 1];\n}`
    }
};
